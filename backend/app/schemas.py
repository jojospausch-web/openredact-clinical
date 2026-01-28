from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


def to_camel_case(string: str) -> str:
    """Convert snake_case to camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class CamelBaseModel(BaseModel):
    """Base model with camelCase aliases for API responses"""
    model_config = ConfigDict(
        alias_generator=to_camel_case,
        populate_by_name=True,
        from_attributes=True
    )


class Annotation(CamelBaseModel):
    """Annotation for evaluation"""
    start: int = Field(ge=0, description="Start position")
    end: int = Field(ge=0, description="End position")
    tag: str = Field(min_length=1, description="Tag name")

    @field_validator('end')
    @classmethod
    def end_after_start(cls, v, info):
        if 'start' in info.data and v <= info.data['start']:
            raise ValueError('end must be greater than start')
        return v


class Scores(CamelBaseModel):
    """Evaluation scores"""
    f1: float = Field(ge=0.0, le=1.0)
    f2: float = Field(ge=0.0, le=1.0)
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    true_positives: int = Field(ge=0)
    false_positives: int = Field(ge=0)
    false_negatives: int = Field(ge=0)


class Pii(CamelBaseModel):
    """Personally Identifiable Information detected in text"""
    start_char: int = Field(ge=0, description="Start character index")
    end_char: int = Field(ge=0, description="End character index")
    tag: str = Field(description="PII tag (e.g., PERSON, DATE)")
    text: str = Field(description="Original PII text")
    score: float = Field(ge=0.0, le=1.0, description="Confidence score")
    recognizer: str = Field(description="Recognizer name")
    start_tok: int = Field(ge=0, description="Start token index")
    end_tok: int = Field(ge=0, description="End token index")


class Token(CamelBaseModel):
    """Text token with metadata"""
    text: str
    has_ws: bool = Field(description="Has trailing whitespace")
    br_count: int = Field(ge=0, description="Line break count")
    start_char: int = Field(ge=0)
    end_char: int = Field(ge=0)


class FindPiisRequest(CamelBaseModel):
    """Request for finding PIIs in text"""
    text: str = Field(min_length=1, max_length=1_000_000)
    language: str = Field(default="de", pattern="^(de|en)$")
    recognizers: Optional[List[str]] = None


class FindPiisResponse(CamelBaseModel):
    """Response with detected PIIs and tokens"""
    piis: List[Pii]
    tokens: List[Token]
    format: str = Field(default="text")


class AnonymizedPii(CamelBaseModel):
    """Anonymized PII replacement"""
    text: str = Field(description="Replacement text")
    id: str = Field(description="Unique ID for this anonymization")


class AnonymizedPiisResponse(CamelBaseModel):
    """Response with anonymized PIIs"""
    anonymized_piis: List[AnonymizedPii]


# Whitelist schemas
class WhitelistEntry(CamelBaseModel):
    """Single whitelist entry"""
    entry: str = Field(min_length=1, max_length=500)


class WhitelistResponse(CamelBaseModel):
    """All whitelist entries"""
    entries: List[str]


class WhitelistBulkUpdate(CamelBaseModel):
    """Bulk whitelist update"""
    entries: List[str] = Field(max_length=10000)


# Template schemas
class TemplateData(CamelBaseModel):
    """Template configuration"""
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default="", max_length=1000)
    default_mechanism: Dict[str, Any]
    mechanisms_by_tag: Dict[str, Dict[str, Any]]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TemplateResponse(CamelBaseModel):
    """Single template"""
    template_id: str
    template: TemplateData


class TemplatesResponse(CamelBaseModel):
    """All templates"""
    templates: Dict[str, TemplateData]


class TemplateImport(CamelBaseModel):
    """Import templates"""
    templates: Dict[str, TemplateData]


class SuccessResponse(CamelBaseModel):
    """Generic success response"""
    success: bool
    message: Optional[str] = None


class ErrorResponse(CamelBaseModel):
    """Error response"""
    detail: str
    error_code: Optional[str] = None


# ===== New NLP Schemas for PR #4 =====

class AnonymizationMechanism(CamelBaseModel):
    """Anonymization mechanism configuration"""
    type: str = Field(description="Mechanism type: redact, replace, hash, partial, mask, shift")
    replacement: Optional[str] = Field(default=None, description="Replacement text for 'replace' type")
    shift_months: Optional[int] = Field(default=None, description="Months to shift dates (can be negative)")
    shift_days: Optional[int] = Field(default=None, description="Days to shift dates (can be negative)")


class FindPIIsRequest(CamelBaseModel):
    """Request for finding PIIs in text using NLP"""
    text: str = Field(..., min_length=1, max_length=100000)
    use_both_models: bool = Field(default=True, description="Use both spaCy and Stanza")


class EntityInfo(CamelBaseModel):
    """Entity detected by NLP"""
    text: str
    start: int
    end: int
    label: str
    source: str
    whitelisted: bool = False


class FindPIIsResponse(CamelBaseModel):
    """Response with detected entities"""
    text: str
    entities: List[EntityInfo]
    total_found: int
    whitelisted_count: int


class AnonymizeRequest(CamelBaseModel):
    """Request for anonymizing text"""
    text: str = Field(..., min_length=1, max_length=100000)
    template_id: Optional[str] = Field(None, description="Template ID to use")


class ReplacementInfo(CamelBaseModel):
    """Information about a single replacement"""
    original: str
    replacement: str
    start: int
    end: int
    label: str
    mechanism: str


class AnonymizeResponse(CamelBaseModel):
    """Response with anonymized text"""
    original_text: str
    anonymized_text: str
    entities_found: int
    entities_anonymized: int
    replacements: List[ReplacementInfo]


# ===== PDF Schemas =====

class UploadPDFResponse(CamelBaseModel):
    pdf_id: str
    filename: str
    file_size_mb: float
    text_preview: str
    text_length: int

class AnonymizePDFRequest(CamelBaseModel):
    pdf_id: str = Field(..., description="ID of uploaded PDF")
    template_id: Optional[str] = Field(None, description="Template to use")
    preserve_layout: bool = Field(True, description="Use hybrid overlay method to preserve layout")
    redact_header: bool = Field(True, description="Black out header region (logos, letterhead)")
    redact_footer: bool = Field(True, description="Black out footer region (phone table, banking)")

class AnonymizePDFResponse(CamelBaseModel):
    anonymized_pdf_id: str
    original_pdf_id: str
    filename: str
    file_size_mb: float
    entities_found: int
    entities_anonymized: int
    method: Optional[str] = Field(None, description="Anonymization method used")
    redacted_count: Optional[int] = Field(None, description="Number of entities redacted")
    shifted_count: Optional[int] = Field(None, description="Number of dates shifted")

class PDFMetadata(CamelBaseModel):
    id: str
    original_filename: str
    file_size_mb: float
    uploaded_at: Optional[str] = None
    created_at: Optional[str] = None
    status: str
    original_pdf_id: Optional[str] = None

class ListPDFsResponse(CamelBaseModel):
    pdfs: List[PDFMetadata]
    total: int
