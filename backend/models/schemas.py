"""
Pydantic models (schemas) for the ATS Resume Analyzer API.
Defines request/response models for all API endpoints.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ComponentScores(BaseModel):
    """Individual component scores for ATS analysis."""
    formatting: float = Field(default=0.0, ge=0.0, le=100.0)
    keywords: float = Field(default=0.0, ge=0.0, le=100.0)
    content: float = Field(default=0.0, ge=0.0, le=100.0)
    skill_validation: float = Field(default=0.0, ge=0.0, le=100.0)
    ats_compatibility: float = Field(default=0.0, ge=0.0, le=100.0)


class JDComparison(BaseModel):
    """Job description comparison results."""
    match_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    semantic_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    skills_gap: List[str] = Field(default_factory=list)


class SkillValidationDetails(BaseModel):
    """Skill validation breakdown with project evidence."""
    validated: List[Dict[str, Any]] = Field(default_factory=list)
    unvalidated: List[str] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    validated_count: int = Field(default=0, ge=0)
    validation_pct: float = Field(default=0.0, ge=0.0, le=100.0)


class IssueDetail(BaseModel):
    """Detailed issue feedback item."""
    issue_title: str = ""
    severity_level: str = "minor"  # critical / moderate / minor
    ats_impact: str = ""
    explanation: str = ""
    where_it_appears: str = ""
    how_to_fix: str = ""
    action_items: List[str] = Field(default_factory=list)
    example_improvement: str = ""


class RecommendationItem(BaseModel):
    """Structured prioritized recommendation item."""
    title: str = ""
    description: str = ""
    priority_icon: str = "🟡"
    priority_label: str = "Priority"
    priority_value: str = "medium"  # critical / high / medium / low
    impact_score: float = 0.0
    category: str = "general"
    action_items: List[str] = Field(default_factory=list)


class LocationAnalysis(BaseModel):
    """Location privacy analysis and recommendations."""
    privacy_risk: str = "none"  # none / low / medium / high
    detected_locations: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    penalty_applied: float = 0.0


class CandidateInfo(BaseModel):
    """Parsed candidate contact information."""
    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""
    portfolio: str = ""


class ResumeProfile(BaseModel):
    """Complete candidate resume profile."""
    candidate_info: CandidateInfo = Field(default_factory=CandidateInfo)
    professional_summary: str = ""
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    action_verbs: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    total_experience_months: int = 0


class ParsedJD(BaseModel):
    """Parsed Job Description structure."""
    job_title: str = ""
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    key_responsibilities: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    """Complete analysis response returned to the user."""
    model_config = ConfigDict(populate_by_name=True, extra="allow")
    
    # Primary score (both casing supported)
    ATS_score: float = Field(default=0.0, alias="ats_score")
    ats_score: float = Field(default=0.0, ge=0.0, le=100.0)
    
    # Component breakdown (scaled to respective max: 20, 25, 25, 15, 15)
    component_scores: ComponentScores = Field(default_factory=ComponentScores)
    
    # Feedback
    issues_summary: List[str] = Field(default_factory=list)
    detailed_feedback: List[IssueDetail] = Field(default_factory=list)
    
    # JD matching
    jd_match_analysis: Optional[JDComparison] = None
    jd_comparison: Optional[JDComparison] = None
    parsed_jd: Optional[Dict[str, Any]] = None
    
    # Skill validation
    skill_validation_details: Optional[SkillValidationDetails] = None
    
    # Keyword analysis
    keyword_match: float = Field(default=0.0, ge=0.0, le=100.0)
    missing_keywords: List[str] = Field(default_factory=list)
    matched_keywords: List[str] = Field(default_factory=list)
    
    # Recommendations & Engine
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    recommendation_summary: str = ""
    estimated_improvement: float = 0.0
    suggestions: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    critical_issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    # Penalties & Bonuses
    penalties: Dict[str, Any] = Field(default_factory=dict)
    bonuses: Dict[str, Any] = Field(default_factory=dict)
    
    # Profile & Privacy
    resume_profile: Optional[Dict[str, Any]] = None
    parsed_data: Optional[Dict[str, Any]] = None
    location_analysis: Optional[Dict[str, Any]] = None
    
    # Skills
    skills: List[str] = Field(default_factory=list)
    experience_months: int = 0
    
    # Score interpretation
    interpretation: str = ""
    
    # Metadata
    record_id: Optional[str] = None
    filename: Optional[str] = None
    file_type: Optional[str] = None
    file_size_bytes: Optional[int] = None


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class AnalyzeResumeRequest(BaseModel):
    """Request model for resume analysis (when using base64 instead of file upload)."""
    filename: str = Field(default="resume.pdf", description="Original filename")
    file_data: str = Field(..., description="Base64-encoded file content")
    jd_text: Optional[str] = Field(None, description="Job description text")
    user_id: str = Field(default="anonymous", description="User identifier")


class BatchAnalyzeRequest(BaseModel):
    """Request model for batch resume analysis."""
    files: List[Dict[str, str]] = Field(
        ...,
        description="List of {filename, file_data (base64)} objects",
    )
    jd_text: Optional[str] = Field(None, description="Job description text")
    user_id: str = Field(default="anonymous", description="User identifier")
    max_concurrent: int = Field(default=3, ge=1, le=10, description="Max concurrent analyses")


class PDFGenerateRequest(BaseModel):
    """Request model for PDF generation."""
    analysis_data: Dict[str, Any] = Field(..., description="Analysis results to include in PDF")
    filename: str = Field(default="ATS_Resume_Report.pdf", description="Output filename")


class GenerateAPIKeyRequest(BaseModel):
    """Request model for API key generation."""
    user_id: str = Field(..., description="User identifier for the API key")


class LoginRequest(BaseModel):
    """Request model for user login."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(default=86400, description="Token expiration in seconds")


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    message: str = "API is running successfully"
    version: str = Field(default="2.0.0")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class HistoryRecord(BaseModel):
    """A single analysis history record."""
    id: str = Field(default="")
    filename: str = Field(default="")
    ats_score: float = Field(default=0.0)
    keyword_match: float = Field(default=0.0)
    created_at: str = Field(default="")


class HistoryResponse(BaseModel):
    """Paginated history response."""
    history: List[HistoryRecord] = Field(default_factory=list)
    count: int = 0
    limit: int = 20
    offset: int = 0
    total: int = 0


class DeleteResponse(BaseModel):
    """Response for delete operations."""
    message: str = "Record deleted successfully"
    record_id: str = Field(default="")


class PDFGenerateResponse(BaseModel):
    """Response for PDF generation."""
    pdf_data: str = Field(default="")  # base64-encoded
    filename: str = Field(default="ATS_Resume_Report.pdf")
    content_type: str = Field(default="application/pdf")
    size_bytes: int = 0


class HTMLReportResponse(BaseModel):
    """Response for HTML report generation."""
    html_content: str = Field(default="")
    content_type: str = Field(default="text/html")


class BatchJobResponse(BaseModel):
    """Response for batch job creation."""
    job_id: str = Field(default="")
    status: str = Field(default="started")
    total_files: int = 0
    message: str = "Batch analysis started"


class BatchJobStatusResponse(BaseModel):
    """Response for batch job status query."""
    job_id: str = Field(default="")
    status: str = Field(default="")
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    current_file: int = 0
    current_filename: str = Field(default="")
    created_at: str = Field(default="")
    completed_at: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None


class BatchSummaryResponse(BaseModel):
    """Aggregate summary of batch analysis results."""
    total_resumes: int = 0
    successful: int = 0
    failed: int = 0
    average_score: float = 0.0
    highest_score: float = 0.0
    lowest_score: float = 0.0
    score_distribution: Dict[str, int] = Field(default_factory=dict)


class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    analysis_cache: Dict[str, Any] = Field(default_factory=dict)
    query_cache: Dict[str, Any] = Field(default_factory=dict)
    nlp_model_cache: Dict[str, Any] = Field(default_factory=dict)


class ModelInfoResponse(BaseModel):
    """BERT model information response."""
    model_path: str = Field(default="")
    model_exists: bool = False
    is_loaded: bool = False
    model_type: Optional[str] = None
    num_labels: Optional[int] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(default="An error occurred")
    error_code: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
