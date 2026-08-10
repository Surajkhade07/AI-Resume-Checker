import logging
import asyncio
import uuid
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, Response
from fastapi.responses import JSONResponse

from backend.api.auth import get_current_user
from backend.models.schemas import AnalysisResponce, ComponentScore, JDComprasion, SkillValidationDetails
from backend.util.file_utils import (
    get_default_grammar_results,
    get_default_skill_validation_results,
    get_default_location_results,
)

logger = logging.getLogger('ats_resume_scorer')

router = APIRouter(prefix='/api/v1', tags=['Analysis'])

def _clean(text: str) -> str:
    for prefix in ('✅', '🌟', '❌', '⚠️', '📝', '🔴', '🟡', '🟢', '🟠', '👍'):
        text = text.lstrip(prefix)
    return text.strip()

@router.post('/analyze-resume', response_model=AnalysisResponce)
async def analyze_resume(
    request: Request,
    resume: UploadFile = File(..., description='Resume file — PDF or DOCX, max 5 MB'),
    job_description: str = Form('', description='Job description text (optional)'),
    user_id: str = Depends(get_current_user),
):
    warnings: List[str] = []

    nlp = getattr(request.app.state, 'nlp', None)
    embedder = getattr(request.app.state, 'embedder', None)

    logger.info(f"Received analyze-resume request from user={user_id}")

    # Timing instrumentation
    from time import perf_counter
    start_ts = perf_counter()

    try:
        file_bytes = await resume.read()
        filename = resume.filename or 'resume'

        from backend.services.resume_parser import (
            FileParsingError,
            FileValidationError,
            parse_resume_file,
        )

        parse_start = perf_counter()
        resume_text, _metadata = parse_resume_file(file_bytes, filename)
        parse_end = perf_counter()
        parse_ms = int((parse_end - parse_start) * 1000)
        logger.info(f"Parsed '{filename}': {len(resume_text)} chars extracted (parse_ms={parse_ms})")

    except Exception as exc:
        logger.error(f'File parsing failed: {exc}')
        raise HTTPException(
            status_code=422,
            detail=f'Could not read or parse the resume: {exc}',
        )

    # Create a background job so analysis continues even if the client disconnects
    job_id = uuid.uuid4().hex
    app_state = request.app.state
    # initialize store if missing
    if not hasattr(app_state, '_job_results'):
        app_state._job_results = {}

    app_state._job_results[job_id] = {
        'status': 'processing',
        'filename': filename,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'timings': {'parse_ms': parse_ms},
    }

    async def _run_analysis_and_store():
        try:
            from backend.services.resume_analyzer import analyze_full_resume

            # Run CPU-bound analysis off the event loop and measure time
            analysis_start = perf_counter()
            result = await asyncio.to_thread(
                analyze_full_resume,
                resume_text,
                nlp,
                embedder,
                job_description,
            )
            analysis_end = perf_counter()
            analysis_ms = int((analysis_end - analysis_start) * 1000)
            logger.info(f"Analysis finished for job {job_id} (analysis_ms={analysis_ms})")

            # Save to persistent history (non-blocking)
            try:
                from backend.database.supabase_db import save_analysis
                saved_id = await save_analysis(user_id, filename, result)
            except Exception as exc_save:
                logger.warning(f'History save failed in background: {exc_save}')
                saved_id = None

            app_state._job_results[job_id] = {
                'status': 'done',
                'result': result,
                'saved_id': saved_id,
                'finished_at': datetime.now(timezone.utc).isoformat(),
                'timings': {'analysis_ms': analysis_ms, 'parse_ms': parse_ms},
            }
        except Exception as exc:
            logger.error(f'Background analysis failed for job {job_id}: {exc}')
            app_state._job_results[job_id] = {'status': 'error', 'error': str(exc)}

    # schedule background job
    asyncio.create_task(_run_analysis_and_store())

    return JSONResponse(status_code=202, content={"job_id": job_id, "status": "processing"})

    # Background job scheduled; result will be available via GET /api/v1/analysis/{job_id}


@router.get('/analysis/{job_id}')
async def get_analysis_status(request: Request, job_id: str):
    app_state = request.app.state
    if not hasattr(app_state, '_job_results'):
        raise HTTPException(status_code=404, detail='Job not found')
    job = app_state._job_results.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    return job

@router.get('/health')
async def health_check(request: Request):
    """Health check — confirms models are loaded and the API is ready."""
    return {
        'status':          'healthy',
        'nlp_loaded':      getattr(request.app.state, 'nlp', None) is not None,
        'embedder_loaded': getattr(request.app.state, 'embedder', None) is not None,
    }

@router.get('/history')
async def get_history(user_id: str = Depends(get_current_user)):
    """Return the signed-in user's past analyses (identity comes from the JWT)."""
    from backend.database.supabase_db import get_user_history
    try:
        return await get_user_history(user_id)
    except Exception as exc:
        logger.error(f'History fetch failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Could not load history: {exc}')


@router.delete('/history/{analysis_id}')
async def delete_history_entry(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete one analysis from the signed-in user's history."""
    from backend.database.supabase_db import delete_analysis
    try:
        success = await delete_analysis(analysis_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail='Analysis not found or not owned by this user.')
        return {'status': 'deleted', 'id': analysis_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f'History delete failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Could not delete: {exc}')
    

@router.post('/generate-pdf')
async def generate_pdf(
    data: AnalysisResponce,
    user_id: str = Depends(get_current_user),
):
    from backend.services.report_generator import generate_html_reports
    from backend.services.pdf_export import generate_combined_pdf
    from fastapi.responses import Response

    try:
        html_docs = generate_html_reports(data.model_dump())
        pdf_bytes = generate_combined_pdf(html_docs)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=ats_report.pdf"
            }
        )
    except Exception as e:
        logger.error(f'Failed to generate PDF: {e}')
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")
    

@router.get('/history/{analysis_id}/pdf')
async def generate_history_pdf(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
):
    from backend.database.supabase_db import get_user_history
    from backend.services.report_generator import generate_html_reports
    from backend.services.pdf_export import generate_combined_pdf
    from fastapi.responses import Response

    history = await get_user_history(user_id)
    analysis_data = next((item["analysis_result"] for item in history if item["id"] == analysis_id), None)

    if not analysis_data:
        raise HTTPException(status_code=404, detail="Analysis not found")

    try:
        html_docs = generate_html_reports(analysis_data)
        pdf_bytes = generate_combined_pdf(html_docs)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ats_report_{analysis_id}.pdf"
            }
        )
    except Exception as e:
        logger.error(f'Failed to generate PDF for history: {e}')
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")