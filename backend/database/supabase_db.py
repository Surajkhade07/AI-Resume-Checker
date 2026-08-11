import logging
import httpx
import json
import sqlite3
import uuid
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict
import asyncio

logger = logging.getLogger('ats_resume_scorer')

from backend.core.config import SUPABASE_URL, SUPABASE_API_KEY

DB_DIR = Path(__file__).resolve().parent
SQLITE_DB_PATH = DB_DIR / "history.db"

def _init_sqlite():
    try:
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    ats_score REAL DEFAULT 0,
                    keyword_match REAL DEFAULT 0,
                    missing_keywords TEXT DEFAULT '[]',
                    analysis_result TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_id, created_at DESC)")
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to initialize SQLite history database: {e}")

_init_sqlite()

def _get_headers():
    if not SUPABASE_URL or not SUPABASE_API_KEY:
        return None
    return {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def _json_default(o):
    if hasattr(o, 'model_dump'):
        return o.model_dump()
    if hasattr(o, '__dict__'):
        return o.__dict__
    return str(o)

def _sqlite_save_analysis(doc_id: str, user_id: str, filename: str, ats_score: float, keyword_match: float, missing_keywords_json: str, result_json: str, created_at: str) -> bool:
    try:
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO analyses (id, user_id, filename, ats_score, keyword_match, missing_keywords, analysis_result, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (doc_id, user_id, filename, ats_score, keyword_match, missing_keywords_json, result_json, created_at))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"SQLite save failed: {e}")
        return False

def _sqlite_get_history(user_id: str) -> List[Dict]:
    try:
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, filename, ats_score, keyword_match, missing_keywords, analysis_result, created_at
                FROM analyses
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
            results = []
            for row in rows:
                try:
                    res_dict = json.loads(row["analysis_result"])
                except Exception:
                    res_dict = {}
                try:
                    missing_kw = json.loads(row["missing_keywords"])
                except Exception:
                    missing_kw = []

                results.append({
                    "id": str(row["id"]),
                    "filename": row["filename"] or "resume",
                    "resume_name": row["filename"] or "resume",
                    "job_title": "Software Engineer",
                    "ats_score": row["ats_score"] or 0,
                    "keyword_match": row["keyword_match"] or 0,
                    "missing_keywords": missing_kw,
                    "date": row["created_at"] or "",
                    "created_at": row["created_at"] or "",
                    "analysis_result": res_dict,
                })
            return results
    except Exception as e:
        logger.error(f"SQLite get_history failed: {e}")
        return []

def _sqlite_delete_analysis(analysis_id: str, user_id: str) -> bool:
    try:
        with sqlite3.connect(SQLITE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM analyses WHERE id = ? AND user_id = ?", (analysis_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"SQLite delete failed: {e}")
        return False

_detected_supabase_table = None

async def _post_supabase(doc: dict, headers: dict) -> bool:
    global _detected_supabase_table
    table = _detected_supabase_table or "analyses"
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}"
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            response = await client.post(url, headers=headers, json=doc)
            if response.status_code in (200, 201):
                logger.info(f"Synced analysis to Supabase table '{table}': {doc.get('id')}")
                return True
            elif response.status_code == 404 and table == "analyses":
                # Try fallback table name
                fb_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/resume_analysis"
                fb_res = await client.post(fb_url, headers=headers, json=doc)
                if fb_res.status_code in (200, 201):
                    _detected_supabase_table = "resume_analysis"
                    return True
    except Exception as exc:
        logger.warning(f"Supabase post skipped (local copy retained): {exc}")
    return False

async def _get_supabase(user_id: str, headers: dict) -> List[Dict]:
    global _detected_supabase_table
    table = _detected_supabase_table or "analyses"
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}"
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            response = await client.get(
                url,
                headers=headers,
                params={"user_id": f"eq.{user_id}", "order": "created_at.desc"}
            )
            if response.status_code == 200:
                docs = response.json()
                supabase_results = []
                for doc in docs:
                    res = doc.get("analysis_result", {})
                    if isinstance(res, str):
                        try:
                            res = json.loads(res)
                        except Exception:
                            res = {}
                    supabase_results.append({
                        "id": str(doc.get("id")),
                        "filename": doc.get("filename", "resume"),
                        "resume_name": doc.get("filename", "resume"),
                        "job_title": "Software Engineer",
                        "ats_score": doc.get("ats_score", 0),
                        "keyword_match": doc.get("keyword_match", 0),
                        "missing_keywords": doc.get("missing_keywords", []),
                        "date": doc.get("created_at", ""),
                        "created_at": doc.get("created_at", ""),
                        "analysis_result": res,
                    })
                return supabase_results
            elif response.status_code == 404 and table == "analyses":
                # Try fallback table name
                fb_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/resume_analysis"
                fb_res = await client.get(
                    fb_url,
                    headers=headers,
                    params={"user_id": f"eq.{user_id}", "order": "created_at.desc"}
                )
                if fb_res.status_code == 200:
                    _detected_supabase_table = "resume_analysis"
                    docs = fb_res.json()
                    supabase_results = []
                    for doc in docs:
                        res = doc.get("analysis_result", {})
                        if isinstance(res, str):
                            try:
                                res = json.loads(res)
                            except Exception:
                                res = {}
                        supabase_results.append({
                            "id": str(doc.get("id")),
                            "filename": doc.get("filename", "resume"),
                            "resume_name": doc.get("filename", "resume"),
                            "job_title": "Software Engineer",
                            "ats_score": doc.get("ats_score", 0),
                            "keyword_match": doc.get("keyword_match", 0),
                            "missing_keywords": doc.get("missing_keywords", []),
                            "date": doc.get("created_at", ""),
                            "created_at": doc.get("created_at", ""),
                            "analysis_result": res,
                        })
                    return supabase_results
    except Exception as exc:
        logger.warning(f"Supabase fetch skipped (using local SQLite): {exc}")
    return []

async def _delete_supabase(analysis_id: str, user_id: str, headers: dict) -> bool:
    global _detected_supabase_table
    table = _detected_supabase_table or "analyses"
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{table}"
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            response = await client.delete(
                url,
                headers=headers,
                params={"id": f"eq.{analysis_id}", "user_id": f"eq.{user_id}"}
            )
            if response.status_code in (200, 204):
                return True
            elif response.status_code == 404:
                fb_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/resume_analysis"
                fb_res = await client.delete(
                    fb_url,
                    headers=headers,
                    params={"id": f"eq.{analysis_id}", "user_id": f"eq.{user_id}"}
                )
                if fb_res.status_code in (200, 204):
                    _detected_supabase_table = "resume_analysis"
                    return True
    except Exception as exc:
        logger.warning(f"Supabase delete skipped: {exc}")
    return False

async def save_analysis(user_id: str, filename: str, analysis_result: Dict) -> Optional[str]:
    doc_id = uuid.uuid4().hex
    serializable_result = json.loads(json.dumps(analysis_result, default=_json_default))

    ats_score = float(serializable_result.get("ats_score", serializable_result.get("ATS_score", 0)))
    keyword_match = float(serializable_result.get("keyword_match", 0))
    missing_keywords = serializable_result.get("missing_keywords", [])
    missing_kw_str = json.dumps(missing_keywords)
    result_str = json.dumps(serializable_result)
    created_at = datetime.now(timezone.utc).isoformat()

    # 1. Always save to local SQLite for 100% guarantee of history persistence
    await asyncio.to_thread(
        _sqlite_save_analysis,
        doc_id, user_id, filename, ats_score, keyword_match, missing_kw_str, result_str, created_at
    )
    logger.info(f"Saved analysis locally in SQLite for user {user_id}: {doc_id}")

    # 2. Also try saving to Supabase if configured
    headers = _get_headers()
    if headers and SUPABASE_URL:
        doc = {
            "id": doc_id,
            "user_id": user_id,
            "filename": filename,
            "ats_score": ats_score,
            "keyword_match": keyword_match,
            "missing_keywords": missing_keywords,
            "created_at": created_at,
            "analysis_result": serializable_result,
        }
        await _post_supabase(doc, headers)

    return doc_id

async def get_user_history(user_id: str) -> List[Dict]:
    # 1. Fetch from local SQLite first
    local_history = await asyncio.to_thread(_sqlite_get_history, user_id)

    # 2. If Supabase is configured, attempt fetch and merge if desired
    headers = _get_headers()
    if headers and SUPABASE_URL:
        supabase_results = await _get_supabase(user_id, headers)
        if supabase_results:
            seen_ids = set()
            combined = []
            for item in supabase_results + local_history:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    combined.append(item)
            combined.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return combined

    return local_history

async def delete_analysis(analysis_id: str, user_id: str) -> bool:
    # 1. Delete from local SQLite
    deleted_local = await asyncio.to_thread(_sqlite_delete_analysis, analysis_id, user_id)

    # 2. Try deleting from Supabase
    headers = _get_headers()
    if headers and SUPABASE_URL:
        await _delete_supabase(analysis_id, user_id, headers)

    return deleted_local
