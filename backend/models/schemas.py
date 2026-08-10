from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ComponentScore(BaseModel):
    formatting: float = 0.0
    keywords: float = Field(default=0.0, alias='keyword')
    content: float = 0.0
    skill_validation: float = 0.0
    ats_compatibility: float = 0.0

    class Config:
        populate_by_name = True

class JDComparison(BaseModel):
    match_percentage: float = 0.0
    semantic_similarity: float = 0.0
    matched_keywords: List[str] = Field(default_factory=list, alias='matching_keyword')
    missing_keywords: List[str] = Field(default_factory=list, alias='missing_keyword')
    skills_gap: List[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True

# Alias for backwards compatibility
JDComprasion = JDComparison

class SkillValidationDetails(BaseModel):
    validated: List[Dict[str, Any]] = Field(default_factory=list, alias='validation')
    unvalidated: List[str] = Field(default_factory=list, alias='unvalidate')
    total: int = 0
    validated_count: int = 0
    validation_pct: float = Field(default=0.0, alias='validated_pct')

    class Config:
        populate_by_name = True

class IssueDetail(BaseModel):
    issue_title: str = ""
    severity_level: str = "moderate"
    ats_impact: str = ""
    explanation: str = ""
    where_it_appears: str = ""
    how_to_fix: str = ""
    action_items: List[str] = Field(default_factory=list, alias='action_item')
    example_improvement: str = ""

    class Config:
        populate_by_name = True

class RecommendationItem(BaseModel):
    title: str = ""
    description: str = ""
    priority_icon: str = "🟡"
    priority_label: str = "Medium Priority"
    priority_value: str = "medium"
    impact_score: float = 0.0
    category: str = "general"
    action_items: List[str] = Field(default_factory=list)

class LocationAnalysis(BaseModel):
    location_found: bool = False
    detected_locations: List[Dict[str, Any]] = Field(default_factory=list)
    privacy_risk: str = "none"
    recommendations: List[str] = Field(default_factory=list)
    penalty_applied: float = 0.0

class CandidateInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None

class ResumeProfile(BaseModel):
    candidate_info: Optional[CandidateInfo] = None
    professional_summary: str = ""
    skills: List[str] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    action_verbs: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    total_experience_months: int = 0

class ParsedJD(BaseModel):
    job_title: str = ""
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    experience_required: str = ""
    education_required: str = ""
    key_responsibilities: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)

class AnalysisResponce(BaseModel):
    ATS_score: float = 0.0
    ats_score: float = 0.0
    component_scores: Optional[Dict[str, float]] = None
    issues_summary: List[str] = Field(default_factory=list, alias='issue_summary')
    critical_issues: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    detailed_feedback: List[IssueDetail] = Field(default_factory=list)
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    recommendation_summary: str = ""
    estimated_improvement: float = 0.0
    jd_match_analysis: Optional[JDComparison] = None
    jd_comparison: Optional[JDComparison] = None
    parsed_jd: Optional[ParsedJD] = None
    skill_validation_details: Optional[SkillValidationDetails] = None
    location_analysis: Optional[LocationAnalysis] = None
    penalties: Dict[str, float] = Field(default_factory=dict)
    bonuses: Dict[str, float] = Field(default_factory=dict)
    resume_profile: Optional[ResumeProfile] = None
    skills: List[str] = Field(default_factory=list)
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    interpretation: str = ""
    keyword_match: float = 0.0
    experience_months: int = 0

    class Config:
        populate_by_name = True

