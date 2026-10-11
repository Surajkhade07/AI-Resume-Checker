"""
Advanced API routes for the ATS Resume Analyzer.
Provides endpoints for resume analysis, batch processing, authentication,
history management, PDF generation, cache management, model info, and health monitoring.
"""
import base64
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import Response, JSONResponse

from backend.core.auth import (
    authenticate_with_google,
    create_access_token,
    generate_api_key,
    get_current_user,
    get_google_auth_url,
    get_optional_user,
)
from backend.core.cache import analysis_cache, nlp_model_cache, query_cache, invalidate_analysis_cache
from backend.core.config import (
    APP_TITLE,
    APP_VERSION,
    APP_ENVIRONMENT,
    MAX_FILE_SIZE_BYTES,
    validate_config,
)
from backend.services.model_loader import initialize_model_state
from backend.services.resume_analyzer import analyze_resume
from backend.services.pdf_export import generate_pdf_report
from backend.services.report_generator import generate_html_report

logger = logging.getLogger('ats_resume_scorer')

router = APIRouter(prefix="/api/v1", tags=["ATS Resume Analyzer"])


# =========================================================================
# Health & Monitoring & Readiness
# =========================================================================

@router.get("/health")
async def health(request: Request):
    """
    Detailed health check endpoint.
    Returns API status, version, environment, cache statistics, and model readiness.
    """
    initialize_model_state(request.app.state)
    cache_stats = {
        "analysis_cache": analysis_cache.get_stats(),
        "query_cache": query_cache.get_stats(),
        "nlp_model_cache": nlp_model_cache.get_stats(),
    }

    return {
        "status": "healthy",
        "message": "API is running successfully",
        "version": APP_VERSION,
        "environment": APP_ENVIRONMENT,
        "cache": cache_stats,
        "models": {
            "nlp": request.app.state.model_status.get("nlp", "idle"),
            "embedder": request.app.state.model_status.get("embedder", "idle"),
        },
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint queried by frontend readinessCheck.
    """
    return {
        "status": "ready",
        "models_ready": True,
        "version": APP_VERSION,
    }


@router.get("/config")
async def get_config():
    """Get current configuration (excluding sensitive keys)."""
    return {
        "title": APP_TITLE,
        "version": APP_VERSION,
        "environment": APP_ENVIRONMENT,
        "max_file_size_mb": MAX_FILE_SIZE_BYTES / (1024 * 1024),
        "config_warnings": validate_config(),
    }


# =========================================================================
# Resume Analysis
# =========================================================================

@router.post("/analyze-resume")
async def analyze_resume_endpoint(
    request: Request,
    file: Optional[UploadFile] = File(None, description="Resume file (PDF, DOCX, or DOC)"),
    resume: Optional[UploadFile] = File(None, description="Alternative form field for resume file"),
    jd_text: Optional[str] = Form(None, description="Job description text for JD matching"),
    job_description: Optional[str] = Form(None, description="Alternative form field for JD text"),
    user_id: str = Depends(get_optional_user),
):
    """
    Analyze a single resume against ATS criteria.
    Accepts resume file as 'resume' or 'file' and JD text as 'job_description' or 'jd_text'.
    Optionally saves analysis to Supabase history if user is authenticated.
    """
    initialize_model_state(request.app.state)

    upload_file = file or resume
    if not upload_file or not upload_file.filename:
        raise HTTPException(
            status_code=400,
            detail="No resume file provided. Please attach a file using the 'resume' or 'file' field."
        )
    
    file_data = await upload_file.read()
    
    if not file_data:
        raise HTTPException(status_code=400, detail="Uploaded resume file is empty")
    
    if len(file_data) > MAX_FILE_SIZE_BYTES:
        size_mb = len(file_data) / (1024 * 1024)
        max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File size ({size_mb:.1f} MB) exceeds maximum allowed ({max_mb:.0f} MB)",
        )
    
    target_jd = jd_text if jd_text is not None else job_description
    
    try:
        result = analyze_resume(
            file_data=file_data,
            filename=upload_file.filename,
            jd_text=target_jd,
            app_state=request.app.state,
        )
        
        # Store in database (SQLite + Supabase)
        record_id = None
        try:
            from backend.database.supabase_db import store_analysis_result
            record_id = store_analysis_result(
                user_id=user_id or "anonymous",
                filename=upload_file.filename,
                analysis_data=result,
                raw_text=result.get('parsed_data', {}).get('raw_text'),
            )
        except Exception as db_err:
            logger.warning(f"Could not persist analysis record to database: {db_err}")
        
        result['record_id'] = record_id
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing resume: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze resume: {str(e)}")


@router.post("/analyze-base64")
async def analyze_resume_base64(
    request: Request,
    data: Dict[str, Any],
    user_id: str = Depends(get_optional_user),
):
    """
    Analyze a resume from base64-encoded file data.
    Useful for API clients that can't use multipart file uploads.
    """
    filename = data.get("filename", "resume.pdf")
    file_data_b64 = data.get("file_data", "")
    jd_text = data.get("jd_text") or data.get("job_description")
    effective_user_id = data.get("user_id") or user_id
    
    if not file_data_b64:
        raise HTTPException(status_code=400, detail="No file_data provided")
    
    try:
        file_data = base64.b64decode(file_data_b64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 data: {e}")
    
    if len(file_data) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds maximum size")
    
    try:
        result = analyze_resume(
            file_data=file_data,
            filename=filename,
            jd_text=jd_text,
            app_state=request.app.state,
        )
        
        record_id = None
        try:
            from backend.database.supabase_db import store_analysis_result
            record_id = store_analysis_result(
                user_id=effective_user_id or "anonymous",
                filename=filename,
                analysis_data=result,
                raw_text=result.get('parsed_data', {}).get('raw_text'),
            )
        except Exception as db_err:
            logger.warning(f"Could not persist analysis record to database: {db_err}")
            
        result['record_id'] = record_id
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing resume from base64: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze resume: {str(e)}")


# =========================================================================
# History Management (SQLite & Supabase)
# =========================================================================

@router.get("/history")
async def get_history_endpoint(
    user_id: str = Depends(get_optional_user),
    limit: int = 50,
    offset: int = 0,
):
    """
    Retrieve analysis history records.
    Returns records for the current user or local records if anonymous.
    """
    try:
        from backend.database.supabase_db import get_user_history
        records = get_user_history(user_id=user_id, limit=limit, offset=offset)
        
        formatted = []
        for r in records:
            analysis_data = r.get('analysis_data') or r.get('analysis_result') or {}
            formatted.append({
                'id': r.get('id'),
                'filename': r.get('filename') or r.get('resume_name') or analysis_data.get('filename', 'resume.pdf'),
                'resume_name': r.get('resume_name') or r.get('filename') or 'resume.pdf',
                'job_title': r.get('job_title') or 'Software Engineer',
                'ats_score': r.get('ats_score') or analysis_data.get('ats_score', 0),
                'keyword_match': r.get('keyword_match') or analysis_data.get('keyword_match', 0),
                'created_at': r.get('created_at'),
                'date': r.get('created_at'),
                'analysis_result': analysis_data,
                'analysis_data': analysis_data,
            })
        return formatted
    except Exception as e:
        logger.error(f"Error retrieving history for user {user_id}: {e}")
        return []


@router.delete("/history/{record_id}")
async def delete_history_endpoint(
    record_id: str,
    user_id: str = Depends(get_optional_user),
):
    """
    Delete a specific analysis record belonging to the user.
    """
    try:
        from backend.database.supabase_db import delete_analysis_record
        success = delete_analysis_record(record_id=record_id, user_id=user_id)
        if not success:
            raise HTTPException(status_code=404, detail="History record not found")
        return {"message": "Record deleted successfully", "id": record_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting history record {record_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete history record: {str(e)}")


@router.get("/history/{record_id}/pdf")
async def get_history_pdf_endpoint(
    record_id: str,
    user_id: str = Depends(get_optional_user),
):
    """
    Generate and stream binary PDF report for a saved history analysis record.
    """
    try:
        from backend.database.supabase_db import get_analysis_by_id
        record = get_analysis_by_id(record_id=record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Analysis record not found")
        
        analysis_data = record.get('analysis_data') or record.get('analysis_result') or {}
        filename = record.get('filename') or record.get('resume_name') or 'resume.pdf'
        pdf_bytes = generate_pdf_report(analysis_data=analysis_data, filename=f"ATS_Report_{filename}.pdf")
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="ats_report_{filename}.pdf"'
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating history PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate history PDF: {str(e)}")


# =========================================================================
# Report Generation
# =========================================================================

@router.post("/generate-pdf")
async def generate_pdf(
    request: Request,
):
    """
    Generate a PDF report from analysis data.
    Returns binary PDF stream for direct browser download.
    """
    try:
        body = await request.json()
        analysis_data = body.get("analysis_data", body)
        pdf_bytes = generate_pdf_report(analysis_data=analysis_data)
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="ats_resume_report.pdf"'
            },
        )
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


@router.post("/generate-html-report")
async def generate_html_report_endpoint(
    request: Request,
):
    """
    Generate an HTML report from analysis data.
    """
    try:
        body = await request.json()
        analysis_data = body.get("analysis_data", body)
        html_content = generate_html_report(analysis_data=analysis_data)
        return {"html_content": html_content, "content_type": "text/html"}
    except Exception as e:
        logger.error(f"Error generating HTML report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate HTML report: {str(e)}")


# =========================================================================
# Authentication
# =========================================================================

@router.post("/auth/login")
async def login(
    request: Request,
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
):
    """
    Login and receive a JWT access token. Accepts form data or JSON body.
    """
    if not email or not password:
        try:
            body = await request.json()
            email = email or body.get("email")
            password = password or body.get("password")
        except Exception:
            pass

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    token = create_access_token(
        user_id=email.split('@')[0],
        email=email,
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 86400,
    }


@router.get("/auth/google")
async def google_auth_start():
    """
    Start Google OAuth — returns the Google authorization URL to redirect to.
    """
    return {"auth_url": get_google_auth_url()}


@router.get("/auth/google/callback")
async def google_auth_callback(code: str):
    """
    Google OAuth callback — exchanges the authorization code for a JWT,
    then redirects the browser to the frontend with the token.
    """
    from urllib.parse import urlencode
    from fastapi.responses import RedirectResponse

    auth_result = authenticate_with_google(code)

    frontend_url = "http://localhost:3000"

    params = urlencode({
        "token": auth_result["access_token"],
        "email": auth_result["user"]["email"],
        "name": auth_result["user"]["name"],
        "picture": auth_result["user"]["picture"],
    })
    return RedirectResponse(url=f"{frontend_url}/login?{params}")


@router.post("/auth/api-key")
async def generate_api_key_endpoint(
    user_id: str = Depends(get_current_user),
):
    """
    Generate a new API key for the authenticated user.
    """
    api_key = generate_api_key(user_id=user_id)
    return {"api_key": api_key, "user_id": user_id, "message": "Store this key securely — it won't be shown again"}


@router.get("/auth/me")
async def get_current_user_info(
    user_id: str = Depends(get_current_user),
):
    """
    Get information about the currently authenticated user.
    """
    return {"user_id": user_id, "authenticated": True}


# =========================================================================
# Cache Management
# =========================================================================

@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics for all cache layers.
    """
    return {
        "analysis_cache": analysis_cache.get_stats(),
        "query_cache": query_cache.get_stats(),
        "nlp_model_cache": nlp_model_cache.get_stats(),
    }


@router.post("/cache/clear")
async def clear_cache(
    cache_name: Optional[str] = None,
):
    """
    Clear specific cache or all caches.
    cache_name options: 'analysis', 'query', 'nlp', or None for all.
    """
    if cache_name == "analysis":
        analysis_cache.clear()
    elif cache_name == "query":
        query_cache.clear()
    elif cache_name == "nlp":
        nlp_model_cache.clear()
    else:
        analysis_cache.clear()
        query_cache.clear()
        nlp_model_cache.clear()
    
    return {"message": f"Cache cleared ({cache_name or 'all'})", "cache_name": cache_name or "all"}


# =========================================================================
# Model Information
# =========================================================================

@router.get("/models/bert")
async def get_bert_model_info():
    """
    Get information about the BERT model status.
    """
    from backend.services.bert_skill_extractor import get_model_info
    return get_model_info()