"""
Supabase database operations for ATS Resume Analyzer.
Handles CRUD operations for analysis history, user data, and report storage.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from supabase import create_client, Client

from backend.core.config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger('ats_resume_scorer')

# Singleton Supabase client instance
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create a singleton Supabase client instance.
    Initializes with URL and service_role key from config.
    Returns: Supabase Client instance
    Raises: ValueError if credentials are not configured
    """
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError(
                "Supabase credentials not configured. "
                "Set SUPABASE_URL and SUPABASE_KEY in environment variables."
            )
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
    return _supabase_client


def store_analysis_result(
    user_id: str,
    filename: str,
    analysis_data: Dict[str, Any],
    raw_text: Optional[str] = None,
) -> Optional[str]:
    """
    Store a resume analysis result in the database.
    
    Args:
        user_id: Unique identifier for the user
        filename: Original filename of the uploaded resume
        analysis_data: Complete analysis result dictionary
        raw_text: Optional raw extracted text from the resume
        
    Returns:
        Record ID if successful, None if failed
    """
    try:
        client = get_supabase_client()
        
        record = {
            'user_id': user_id,
            'filename': filename,
            'ats_score': analysis_data.get('ats_score', 0),
            'keyword_match': analysis_data.get('keyword_match', 0),
            'analysis_data': analysis_data,
            'raw_text': raw_text,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        
        response = client.table('analysis_history').insert(record).execute()
        
        if response.data and len(response.data) > 0:
            record_id = response.data[0].get('id')
            logger.info(f"Stored analysis result for {filename} (ID: {record_id})")
            return record_id
        
        logger.warning(f"Failed to store analysis result for {filename}: no data returned")
        return None
        
    except Exception as e:
        logger.error(f"Error storing analysis result: {e}")
        return None


def get_user_history(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Retrieve analysis history for a specific user.
    
    Args:
        user_id: Unique identifier for the user
        limit: Maximum number of records to return (default 20)
        offset: Number of records to skip for pagination
        
    Returns:
        List of analysis history records (sorted by most recent first)
    """
    try:
        client = get_supabase_client()
        
        response = (
            client.table('analysis_history')
            .select('id, filename, ats_score, keyword_match, analysis_data, created_at')
            .eq('user_id', user_id)
            .order('created_at', desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )
        
        return response.data if response.data else []
        
    except Exception as e:
        logger.error(f"Error retrieving history for user {user_id}: {e}")
        return []


def get_analysis_by_id(record_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific analysis record by its ID.
    
    Args:
        record_id: The unique ID of the analysis record
        
    Returns:
        Analysis record dictionary if found, None otherwise
    """
    try:
        client = get_supabase_client()
        
        response = (
            client.table('analysis_history')
            .select('*')
            .eq('id', record_id)
            .limit(1)
            .execute()
        )
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        logger.warning(f"Analysis record {record_id} not found")
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving analysis {record_id}: {e}")
        return None


def delete_analysis_record(record_id: str, user_id: str) -> bool:
    """
    Delete a specific analysis record (with ownership check).
    
    Args:
        record_id: The unique ID of the record to delete
        user_id: User ID for ownership verification
        
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        client = get_supabase_client()
        
        response = (
            client.table('analysis_history')
            .delete()
            .eq('id', record_id)
            .eq('user_id', user_id)
            .execute()
        )
        
        if response.data and len(response.data) > 0:
            logger.info(f"Deleted analysis record {record_id}")
            return True
        
        logger.warning(f"Analysis record {record_id} not found or not owned by user {user_id}")
        return False
        
    except Exception as e:
        logger.error(f"Error deleting analysis {record_id}: {e}")
        return False


def count_user_records(user_id: str) -> int:
    """
    Count total analysis records for a user.
    
    Args:
        user_id: Unique identifier for the user
        
    Returns:
        Total count of records
    """
    try:
        client = get_supabase_client()
        
        response = (
            client.table('analysis_history')
            .select('id', count='exact')
            .eq('user_id', user_id)
            .execute()
        )
        
        return response.count if hasattr(response, 'count') else 0
        
    except Exception as e:
        logger.error(f"Error counting records for user {user_id}: {e}")
        return 0


def store_user_feedback(
    record_id: str,
    user_id: str,
    rating: int,
    comments: Optional[str] = None,
) -> bool:
    """
    Store user feedback on an analysis result.
    
    Args:
        record_id: Analysis record ID to attach feedback to
        user_id: User providing the feedback
        rating: Rating score (e.g., 1-5)
        comments: Optional textual feedback
        
    Returns:
        True if stored successfully, False otherwise
    """
    try:
        client = get_supabase_client()
        
        feedback_record = {
            'analysis_id': record_id,
            'user_id': user_id,
            'rating': rating,
            'comments': comments,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        
        response = client.table('user_feedback').insert(feedback_record).execute()
        return bool(response.data and len(response.data) > 0)
        
    except Exception as e:
        logger.error(f"Error storing feedback for analysis {record_id}: {e}")
        return False