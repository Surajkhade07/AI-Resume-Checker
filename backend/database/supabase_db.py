"""
Database operations for ATS Resume Analyzer.
Provides persistent storage using local SQLite database with Supabase synchronization.
Handles CRUD operations for analysis history, user data, and report storage.
"""
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from backend.core.config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger('ats_resume_scorer')

# Local SQLite database path
SQLITE_DB_PATH = Path(__file__).resolve().parent / "history.db"

# Singleton Supabase client instance
_supabase_client: Optional[Client] = None


def _init_sqlite_db():
    """Initialize local SQLite database table if not exists."""
    try:
        SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(SQLITE_DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    filename TEXT,
                    resume_name TEXT,
                    job_title TEXT,
                    ats_score REAL,
                    keyword_match REAL,
                    missing_keywords TEXT,
                    analysis_result TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()
    except Exception as e:
        logger.error(f"Error initializing local SQLite database: {e}")


# Initialize SQLite database immediately
_init_sqlite_db()


def _sqlite_save_analysis(
    record_id: str,
    user_id: str,
    filename: str,
    ats_score: float,
    keyword_match: float,
    missing_keywords: List[str],
    analysis_data: Dict[str, Any],
    created_at: str,
) -> bool:
    """Save an analysis record to local SQLite."""
    try:
        with sqlite3.connect(str(SQLITE_DB_PATH)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO analyses (
                    id, user_id, filename, resume_name, job_title,
                    ats_score, keyword_match, missing_keywords,
                    analysis_result, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record_id,
                user_id or "anonymous",
                filename,
                filename,
                analysis_data.get('target_role') or analysis_data.get('job_title') or 'Software Engineer',
                float(ats_score),
                float(keyword_match),
                json.dumps(missing_keywords or []),
                json.dumps(analysis_data),
                created_at,
            ))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving to SQLite: {e}")
        return False


def _sqlite_get_history(user_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Retrieve history from local SQLite."""
    try:
        with sqlite3.connect(str(SQLITE_DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if user_id and user_id != "anonymous":
                cursor.execute("""
                    SELECT * FROM analyses
                    WHERE user_id = ? OR user_id = 'anonymous'
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM analyses
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            rows = cursor.fetchall()
            results = []
            for row in rows:
                r_dict = dict(row)
                res_str = r_dict.get('analysis_result') or '{}'
                try:
                    res_data = json.loads(res_str)
                except Exception:
                    res_data = {}
                results.append({
                    'id': r_dict.get('id'),
                    'user_id': r_dict.get('user_id'),
                    'filename': r_dict.get('filename') or r_dict.get('resume_name') or 'resume.pdf',
                    'resume_name': r_dict.get('resume_name') or r_dict.get('filename') or 'resume.pdf',
                    'job_title': r_dict.get('job_title') or 'Software Engineer',
                    'ats_score': r_dict.get('ats_score') or 0,
                    'keyword_match': r_dict.get('keyword_match') or 0,
                    'created_at': r_dict.get('created_at'),
                    'date': r_dict.get('created_at'),
                    'analysis_result': res_data,
                    'analysis_data': res_data,
                })
            return results
    except Exception as e:
        logger.error(f"Error fetching history from SQLite: {e}")
        return []


def _sqlite_get_analysis_by_id(record_id: str) -> Optional[Dict[str, Any]]:
    """Get single analysis from SQLite by ID."""
    try:
        with sqlite3.connect(str(SQLITE_DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM analyses WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            if row:
                r_dict = dict(row)
                res_str = r_dict.get('analysis_result') or '{}'
                try:
                    res_data = json.loads(res_str)
                except Exception:
                    res_data = {}
                return {
                    'id': r_dict.get('id'),
                    'user_id': r_dict.get('user_id'),
                    'filename': r_dict.get('filename') or 'resume.pdf',
                    'resume_name': r_dict.get('resume_name') or 'resume.pdf',
                    'job_title': r_dict.get('job_title') or 'Software Engineer',
                    'ats_score': r_dict.get('ats_score') or 0,
                    'keyword_match': r_dict.get('keyword_match') or 0,
                    'created_at': r_dict.get('created_at'),
                    'date': r_dict.get('created_at'),
                    'analysis_result': res_data,
                    'analysis_data': res_data,
                }
    except Exception as e:
        logger.error(f"Error fetching record {record_id} from SQLite: {e}")
    return None


def _sqlite_delete_analysis(record_id: str, user_id: Optional[str] = None) -> bool:
    """Delete analysis from SQLite."""
    try:
        with sqlite3.connect(str(SQLITE_DB_PATH)) as conn:
            cursor = conn.cursor()
            if user_id and user_id != "anonymous":
                cursor.execute("DELETE FROM analyses WHERE id = ? AND (user_id = ? OR user_id = 'anonymous')", (record_id, user_id))
            else:
                cursor.execute("DELETE FROM analyses WHERE id = ?", (record_id,))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting record {record_id} from SQLite: {e}")
        return False


def get_supabase_client() -> Optional[Client]:
    """
    Get or create a singleton Supabase client instance.
    Initializes with URL and service_role key from config.
    Returns: Supabase Client instance or None if not configured.
    """
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            return None
        try:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize Supabase client: {e}")
            return None
    return _supabase_client


def store_analysis_result(
    user_id: str,
    filename: str,
    analysis_data: Dict[str, Any],
    raw_text: Optional[str] = None,
) -> Optional[str]:
    """
    Store a resume analysis result in the database (local SQLite and Supabase).
    
    Args:
        user_id: Unique identifier for the user (or 'anonymous')
        filename: Original filename of the uploaded resume
        analysis_data: Complete analysis result dictionary
        raw_text: Optional raw extracted text from the resume
        
    Returns:
        Record ID if successful, None if failed
    """
    record_id = str(uuid.uuid4())
    ats_score = float(analysis_data.get('ats_score') or analysis_data.get('ATS_score') or 0)
    keyword_match = float(analysis_data.get('keyword_match') or 0)
    missing_keywords = analysis_data.get('missing_keywords') or []
    created_at = datetime.now(timezone.utc).isoformat()

    # 1. Always persist to local SQLite for 100% guarantee of history storage
    _sqlite_save_analysis(
        record_id=record_id,
        user_id=user_id or "anonymous",
        filename=filename,
        ats_score=ats_score,
        keyword_match=keyword_match,
        missing_keywords=missing_keywords,
        analysis_data=analysis_data,
        created_at=created_at,
    )
    logger.info(f"Stored analysis result locally in SQLite (ID: {record_id})")

    # 2. Also sync to Supabase if available
    client = get_supabase_client()
    if client:
        # Table 1: resume_analysis (the verified table in user's Supabase instance)
        try:
            resume_analysis_doc = {
                'id': record_id,
                'filename': filename,
                'resume_name': filename,
                'job_title': analysis_data.get('target_role') or analysis_data.get('job_title') or 'Software Engineer',
                'ats_score': int(round(ats_score)),
                'keyword_match': int(round(keyword_match)),
                'missing_keywords': [str(k) for k in missing_keywords] if isinstance(missing_keywords, list) else [],
                'created_at': created_at,
                'analysis_result': {**analysis_data, 'user_id': user_id or 'anonymous', 'filename': filename},
            }
            res = client.table('resume_analysis').insert(resume_analysis_doc).execute()
            if res.data:
                logger.info(f"Synced analysis result to Supabase 'resume_analysis' table (ID: {record_id})")
                return record_id
        except Exception as e_ra:
            logger.warning(f"Could not insert into Supabase 'resume_analysis': {e_ra}")

        # Table 2: analysis_history fallback (if created)
        try:
            history_doc = {
                'id': record_id,
                'user_id': user_id or 'anonymous',
                'filename': filename,
                'ats_score': int(round(ats_score)),
                'keyword_match': int(round(keyword_match)),
                'analysis_data': analysis_data,
                'raw_text': raw_text,
                'created_at': created_at,
            }
            res = client.table('analysis_history').insert(history_doc).execute()
            if res.data:
                logger.info(f"Synced analysis result to Supabase 'analysis_history' table (ID: {record_id})")
                return record_id
        except Exception as e_ah:
            logger.debug(f"Fallback insert to 'analysis_history' skipped: {e_ah}")

    return record_id


def get_user_history(
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Retrieve analysis history for a specific user (merging SQLite and Supabase).
    
    Args:
        user_id: Unique identifier for the user (or 'anonymous' / None)
        limit: Maximum number of records to return
        offset: Number of records to skip for pagination
        
    Returns:
        List of analysis history records (sorted by most recent first)
    """
    # 1. Fetch from local SQLite
    sqlite_records = _sqlite_get_history(user_id=user_id, limit=limit, offset=offset)

    # 2. Fetch from Supabase
    supabase_records: List[Dict[str, Any]] = []
    client = get_supabase_client()
    if client:
        # Check 'resume_analysis' table
        try:
            res = client.table('resume_analysis').select('*').order('created_at', desc=True).limit(limit).offset(offset).execute()
            if res.data:
                for row in res.data:
                    analysis_result = row.get('analysis_result') or {}
                    if isinstance(analysis_result, str):
                        try:
                            analysis_result = json.loads(analysis_result)
                        except Exception:
                            analysis_result = {}

                    row_user = row.get('user_id') or analysis_result.get('user_id')
                    if user_id and user_id != 'anonymous' and row_user:
                        if row_user != user_id and row_user != 'anonymous':
                            continue

                    supabase_records.append({
                        'id': str(row.get('id')),
                        'user_id': row_user or user_id or 'anonymous',
                        'filename': row.get('filename') or row.get('resume_name') or 'resume.pdf',
                        'resume_name': row.get('resume_name') or row.get('filename') or 'resume.pdf',
                        'job_title': row.get('job_title') or 'Software Engineer',
                        'ats_score': row.get('ats_score') or analysis_result.get('ats_score') or 0,
                        'keyword_match': row.get('keyword_match') or analysis_result.get('keyword_match') or 0,
                        'created_at': row.get('created_at'),
                        'date': row.get('created_at'),
                        'analysis_result': analysis_result,
                        'analysis_data': analysis_result,
                    })
        except Exception as e_ra:
            logger.warning(f"Could not fetch history from Supabase 'resume_analysis': {e_ra}")

        # Check 'analysis_history' table fallback if resume_analysis had nothing
        if not supabase_records:
            try:
                query = client.table('analysis_history').select('*')
                if user_id and user_id != 'anonymous':
                    query = query.eq('user_id', user_id)
                res = query.order('created_at', desc=True).limit(limit).offset(offset).execute()
                if res.data:
                    for row in res.data:
                        adata = row.get('analysis_data') or row.get('analysis_result') or {}
                        supabase_records.append({
                            'id': str(row.get('id')),
                            'user_id': row.get('user_id') or user_id or 'anonymous',
                            'filename': row.get('filename') or 'resume.pdf',
                            'resume_name': row.get('filename') or 'resume.pdf',
                            'ats_score': row.get('ats_score') or adata.get('ats_score') or 0,
                            'keyword_match': row.get('keyword_match') or adata.get('keyword_match') or 0,
                            'created_at': row.get('created_at'),
                            'date': row.get('created_at'),
                            'analysis_result': adata,
                            'analysis_data': adata,
                        })
            except Exception as e_ah:
                logger.debug(f"Supabase 'analysis_history' fetch skipped: {e_ah}")

    # 3. Merge and deduplicate by ID
    seen_ids = set()
    merged: List[Dict[str, Any]] = []

    # Prioritize Supabase records first, then SQLite
    for item in supabase_records + sqlite_records:
        item_id = str(item.get('id'))
        if item_id and item_id not in seen_ids:
            seen_ids.add(item_id)
            merged.append(item)

    # Sort descending by created_at
    merged.sort(key=lambda x: str(x.get('created_at') or ''), reverse=True)
    return merged[:limit]


def get_analysis_by_id(record_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific analysis record by its ID.
    
    Args:
        record_id: The unique ID of the analysis record
        
    Returns:
        Analysis record dictionary if found, None otherwise
    """
    # 1. Try local SQLite
    local_rec = _sqlite_get_analysis_by_id(record_id)
    if local_rec:
        return local_rec

    # 2. Try Supabase
    client = get_supabase_client()
    if client:
        # Check 'resume_analysis'
        try:
            res = client.table('resume_analysis').select('*').eq('id', record_id).limit(1).execute()
            if res.data and len(res.data) > 0:
                row = res.data[0]
                adata = row.get('analysis_result') or {}
                if isinstance(adata, str):
                    try:
                        adata = json.loads(adata)
                    except Exception:
                        adata = {}
                return {
                    'id': str(row.get('id')),
                    'filename': row.get('filename') or row.get('resume_name') or 'resume.pdf',
                    'resume_name': row.get('resume_name') or row.get('filename') or 'resume.pdf',
                    'ats_score': row.get('ats_score') or 0,
                    'keyword_match': row.get('keyword_match') or 0,
                    'created_at': row.get('created_at'),
                    'date': row.get('created_at'),
                    'analysis_result': adata,
                    'analysis_data': adata,
                }
        except Exception as e:
            logger.warning(f"Error checking Supabase 'resume_analysis' for {record_id}: {e}")

        # Check 'analysis_history'
        try:
            res = client.table('analysis_history').select('*').eq('id', record_id).limit(1).execute()
            if res.data and len(res.data) > 0:
                row = res.data[0]
                adata = row.get('analysis_data') or row.get('analysis_result') or {}
                return {
                    'id': str(row.get('id')),
                    'filename': row.get('filename') or 'resume.pdf',
                    'resume_name': row.get('filename') or 'resume.pdf',
                    'ats_score': row.get('ats_score') or 0,
                    'keyword_match': row.get('keyword_match') or 0,
                    'created_at': row.get('created_at'),
                    'date': row.get('created_at'),
                    'analysis_result': adata,
                    'analysis_data': adata,
                }
        except Exception as e:
            logger.debug(f"Error checking Supabase 'analysis_history' for {record_id}: {e}")

    logger.warning(f"Analysis record {record_id} not found in SQLite or Supabase")
    return None


def delete_analysis_record(record_id: str, user_id: Optional[str] = None) -> bool:
    """
    Delete a specific analysis record from SQLite and Supabase.
    
    Args:
        record_id: The unique ID of the record to delete
        user_id: User ID for ownership verification
        
    Returns:
        True if deletion was successful from either store, False otherwise
    """
    deleted_local = _sqlite_delete_analysis(record_id, user_id=user_id)

    deleted_supabase = False
    client = get_supabase_client()
    if client:
        try:
            res = client.table('resume_analysis').delete().eq('id', record_id).execute()
            if res.data and len(res.data) > 0:
                deleted_supabase = True
        except Exception as e:
            logger.warning(f"Error deleting from Supabase 'resume_analysis': {e}")

        try:
            res = client.table('analysis_history').delete().eq('id', record_id).execute()
            if res.data and len(res.data) > 0:
                deleted_supabase = True
        except Exception as e:
            logger.debug(f"Error deleting from Supabase 'analysis_history': {e}")

    return deleted_local or deleted_supabase


def count_user_records(user_id: Optional[str] = None) -> int:
    """
    Count total analysis records for a user.
    """
    history = get_user_history(user_id=user_id)
    return len(history)


def store_user_feedback(
    record_id: str,
    user_id: str,
    rating: int,
    comments: Optional[str] = None,
) -> bool:
    """Store user feedback on an analysis result."""
    client = get_supabase_client()
    if client:
        try:
            feedback_record = {
                'analysis_id': record_id,
                'user_id': user_id or 'anonymous',
                'rating': rating,
                'comments': comments,
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
            response = client.table('user_feedback').insert(feedback_record).execute()
            return bool(response.data and len(response.data) > 0)
        except Exception as e:
            logger.error(f"Error storing feedback in Supabase: {e}")
    return True