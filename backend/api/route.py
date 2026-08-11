import asyncio
import logging
import uuid

from datetime import datetime, timezone
from time import perf_counter

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import JSONResponse, Response

from backend.api.auth import get_current_user
from backend.models.schemas import AnalysisResponce


logger = logging.getLogger("ats_resume_scorer")

router = APIRouter(
    prefix="/api/v1",
    tags=["Analysis"],
)


def _clean(text: str) -> str:
    for prefix in (
        "✅",
        "🌟",
        "❌",
        "⚠️",
        "📝",
        "🔴",
        "🟡",
        "🟢",
        "🟠",
        "👍",
    ):
        text = text.lstrip(prefix)

    return text.strip()


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "ATS Resume Analysis API",
    }


@router.get("/ready")
async def readiness_check(request: Request):
    models_ready = getattr(
        request.app.state,
        "models_ready",
        False,
    )

    nlp_loaded = (
        getattr(
            request.app.state,
            "nlp",
            None,
        )
        is not None
    )

    embedder_loaded = (
        getattr(
            request.app.state,
            "embedder",
            None,
        )
        is not None
    )

    if not models_ready:
        return JSONResponse(
            status_code=503,
            content={
                "status": "starting",
                "models_ready": False,
                "nlp_loaded": nlp_loaded,
                "embedder_loaded": embedder_loaded,
                "error": getattr(
                    request.app.state,
                    "models_error",
                    None,
                ),
            },
        )

    return {
        "status": "ready",
        "models_ready": True,
        "nlp_loaded": True,
        "embedder_loaded": True,
    }


@router.post("/analyze-resume")
async def analyze_resume(
    request: Request,
    resume: UploadFile = File(...),
    job_description: str = Form(""),
    user_id: str = Depends(get_current_user),
):
    logger.info(
        "Received analyze-resume request from user=%s",
        user_id,
    )

    models_ready = getattr(
        request.app.state,
        "models_ready",
        False,
    )

    if not models_ready:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI models are still loading. "
                "Please try again in a few seconds."
            ),
        )

    try:
        file_bytes = await resume.read()
        filename = resume.filename or "resume"

    except Exception as exc:
        logger.exception(
            "Failed to read uploaded file: %s",
            exc,
        )

        raise HTTPException(
            status_code=422,
            detail=(
                f"Could not read uploaded resume: {exc}"
            ),
        )

    try:
        from backend.services.resume_parser import (
            parse_resume_file,
        )

        parse_start = perf_counter()

        resume_text, _metadata = parse_resume_file(
            file_bytes,
            filename,
        )

        parse_end = perf_counter()

        parse_ms = int(
            (parse_end - parse_start) * 1000
        )

        logger.info(
            "Parsed '%s': %d chars extracted "
            "(parse_ms=%d)",
            filename,
            len(resume_text),
            parse_ms,
        )

    except Exception as exc:
        logger.exception(
            "File parsing failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=422,
            detail=(
                f"Could not read or parse "
                f"the resume: {exc}"
            ),
        )

    if not resume_text or not resume_text.strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "No readable text could be extracted "
                "from the uploaded resume."
            ),
        )

    job_id = uuid.uuid4().hex

    app_state = request.app.state

    if not hasattr(
        app_state,
        "_job_results",
    ):
        app_state._job_results = {}

    app_state._job_results[job_id] = {
        "status": "processing",
        "filename": filename,
        "created_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "timings": {
            "parse_ms": parse_ms,
        },
    }

    async def _run_analysis_and_store():
        try:
            from backend.services.resume_analyzer import (
                analyze_full_resume,
            )

            nlp = getattr(
                app_state,
                "nlp",
                None,
            )

            embedder = getattr(
                app_state,
                "embedder",
                None,
            )

            if nlp is None:
                raise RuntimeError(
                    "spaCy model is not available."
                )

            if embedder is None:
                raise RuntimeError(
                    "Sentence Transformer model "
                    "is not available."
                )

            semaphore = getattr(
                app_state,
                "analysis_semaphore",
                None,
            )

            analysis_start = perf_counter()

            if semaphore is not None:
                async with semaphore:
                    result = await asyncio.to_thread(
                        analyze_full_resume,
                        resume_text,
                        nlp,
                        embedder,
                        job_description,
                    )
            else:
                result = await asyncio.to_thread(
                    analyze_full_resume,
                    resume_text,
                    nlp,
                    embedder,
                    job_description,
                )

            analysis_end = perf_counter()

            analysis_ms = int(
                (analysis_end - analysis_start)
                * 1000
            )

            saved_id = None

            try:
                from backend.database.supabase_db import (
                    save_analysis,
                )

                saved_id = await save_analysis(
                    user_id,
                    filename,
                    result,
                )

            except Exception as exc_save:
                logger.warning(
                    "History save failed for job %s: %s",
                    job_id,
                    exc_save,
                )

            app_state._job_results[job_id] = {
                "status": "done",
                "result": result,
                "saved_id": saved_id,
                "finished_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "timings": {
                    "analysis_ms": analysis_ms,
                    "parse_ms": parse_ms,
                },
            }

            logger.info(
                "Job %s completed successfully",
                job_id,
            )

        except asyncio.CancelledError:
            app_state._job_results[job_id] = {
                "status": "cancelled",
            }

            raise

        except Exception as exc:
            logger.exception(
                "Background analysis failed "
                "for job %s: %s",
                job_id,
                exc,
            )

            app_state._job_results[job_id] = {
                "status": "error",
                "error": str(exc),
            }

    asyncio.create_task(
        _run_analysis_and_store()
    )

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": "processing",
        },
    )


@router.get("/analysis/{job_id}")
async def get_analysis_status(
    request: Request,
    job_id: str,
):
    job_results = getattr(
        request.app.state,
        "_job_results",
        None,
    )

    if job_results is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    job = job_results.get(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return job


@router.get("/history")
async def get_history(
    user_id: str = Depends(get_current_user),
):
    from backend.database.supabase_db import (
        get_user_history,
    )

    try:
        return await get_user_history(user_id)

    except Exception as exc:
        logger.exception(
            "History fetch failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not load history: {exc}"
            ),
        )


@router.delete("/history/{analysis_id}")
async def delete_history_entry(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
):
    from backend.database.supabase_db import (
        delete_analysis,
    )

    try:
        success = await delete_analysis(
            analysis_id,
            user_id,
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Analysis not found or "
                    "not owned by this user."
                ),
            )

        return {
            "status": "deleted",
            "id": analysis_id,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "History delete failed: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not delete: {exc}"
            ),
        )


@router.post("/generate-pdf")
async def generate_pdf(
    data: AnalysisResponce,
    user_id: str = Depends(get_current_user),
):
    from backend.services.report_generator import (
        generate_html_reports,
    )

    from backend.services.pdf_export import (
        generate_combined_pdf,
    )

    try:
        html_docs = generate_html_reports(
            data.model_dump()
        )

        pdf_bytes = generate_combined_pdf(
            html_docs
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    "attachment; "
                    "filename=ats_report.pdf"
                )
            },
        )

    except Exception as exc:
        logger.exception(
            "Failed to generate PDF: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to generate PDF: {exc}"
            ),
        )


@router.get("/history/{analysis_id}/pdf")
async def generate_history_pdf(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
):
    from backend.database.supabase_db import (
        get_user_history,
    )

    from backend.services.report_generator import (
        generate_html_reports,
    )

    from backend.services.pdf_export import (
        generate_combined_pdf,
    )

    try:
        history = await get_user_history(
            user_id
        )

    except Exception as exc:
        logger.exception(
            "Failed to fetch history: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Could not load history: {exc}"
            ),
        )

    analysis_data = next(
        (
            item.get("analysis_result")
            for item in history
            if item.get("id") == analysis_id
        ),
        None,
    )

    if not analysis_data:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found",
        )

    try:
        html_docs = generate_html_reports(
            analysis_data
        )

        pdf_bytes = generate_combined_pdf(
            html_docs
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f"attachment; "
                    f"filename=ats_report_{analysis_id}.pdf"
                )
            },
        )

    except Exception as exc:
        logger.exception(
            "Failed to generate PDF for history: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to generate PDF: {exc}"
            ),
        )