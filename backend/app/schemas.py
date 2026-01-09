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
    templates: Dict[str, TemplateData] = Field(max_length=1000)


class SuccessResponse(CamelBaseModel):
    """Generic success response"""
    success: bool
    message: Optional[str] = None


class ErrorResponse(CamelBaseModel):
    """Error response"""
    detail: str
    error_code: Optional[str] = None
