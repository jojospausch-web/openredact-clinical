"""
API Router - All API endpoints with NLP integration
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status

from app.schemas import (
    # Whitelist schemas
    WhitelistResponse,
    WhitelistEntry,
    WhitelistBulkUpdate,
    # Template schemas
    TemplateData,
    TemplateResponse,
    TemplatesResponse,
    TemplateImport,
    # Response schemas
    SuccessResponse,
    # New NLP schemas
    FindPIIsRequest,
    FindPIIsResponse,
    AnonymizeRequest,
    AnonymizeResponse,
    AnonymizationMechanism,
)
from app.storage import WhitelistStorage, TemplateStorage
from app.nlp import get_nlp_manager
from app.anonymizer import anonymizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


# ===== WHITELIST ENDPOINTS =====

@router.get(
    "/whitelist",
    response_model=WhitelistResponse,
    summary="Get all whitelist entries"
)
async def get_whitelist():
    """Retrieve all whitelist entries"""
    entries = WhitelistStorage.get_all()
    return WhitelistResponse(entries=entries)


@router.post(
    "/whitelist",
    response_model=SuccessResponse,
    summary="Add whitelist entry",
    status_code=status.HTTP_201_CREATED
)
async def add_whitelist_entry(entry: WhitelistEntry):
    """Add new entry to whitelist"""
    success = WhitelistStorage.add(entry.entry)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Entry already exists"
        )
    return SuccessResponse(success=True, message="Entry added")


@router.delete(
    "/whitelist/{entry}",
    response_model=SuccessResponse,
    summary="Remove whitelist entry"
)
async def remove_whitelist_entry(entry: str):
    """Remove entry from whitelist"""
    success = WhitelistStorage.remove(entry)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found"
        )
    return SuccessResponse(success=True, message="Entry removed")


@router.put(
    "/whitelist",
    response_model=SuccessResponse,
    summary="Replace entire whitelist"
)
async def update_whitelist(bulk: WhitelistBulkUpdate):
    """Replace all whitelist entries"""
    success = WhitelistStorage.set_all(bulk.entries)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update whitelist (limit exceeded or storage error)"
        )
    return SuccessResponse(success=True, message=f"Whitelist updated with {len(bulk.entries)} entries")


# ===== TEMPLATE ENDPOINTS =====

@router.get(
    "/templates",
    response_model=TemplatesResponse,
    summary="Get all templates"
)
async def get_templates():
    """Retrieve all anonymization templates"""
    templates = TemplateStorage.get_all()
    return TemplatesResponse(templates=templates)


@router.post(
    "/templates/import",
    response_model=SuccessResponse,
    summary="Import templates"
)
async def import_templates(import_data: TemplateImport):
    """Import multiple templates"""
    success = TemplateStorage.import_templates(import_data.templates)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to import templates (limit exceeded)"
        )
    return SuccessResponse(
        success=True, 
        message=f"Imported {len(import_data.templates)} templates"
    )


@router.get(
    "/templates/{template_id}",
    response_model=TemplateResponse,
    summary="Get single template"
)
async def get_template(template_id: str):
    """Retrieve specific template"""
    template = TemplateStorage.get(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found"
        )
    return TemplateResponse(template_id=template_id, template=template)


@router.post(
    "/templates/{template_id}",
    response_model=SuccessResponse,
    summary="Create or update template",
    status_code=status.HTTP_201_CREATED
)
async def save_template(template_id: str, template_data: TemplateData):
    """Create or update anonymization template"""
    success = TemplateStorage.save(template_id, template_data.model_dump())
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to save template (limit reached or storage error)"
        )
    return SuccessResponse(success=True, message=f"Template '{template_id}' saved")


@router.delete(
    "/templates/{template_id}",
    response_model=SuccessResponse,
    summary="Delete template"
)
async def delete_template(template_id: str):
    """Delete template"""
    success = TemplateStorage.delete(template_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete template"
        )
    return SuccessResponse(success=True, message=f"Template '{template_id}' deleted")


# ===== NLP ENDPOINTS =====

@router.post(
    "/find-piis",
    response_model=FindPIIsResponse,
    summary="Find PIIs in text",
    description="Detect personally identifiable information in German text using NLP"
)
async def find_piis(request: FindPIIsRequest):
    """
    Find PIIs in text using spaCy and Stanza NLP models.
    Returns detected entities with their positions and labels.
    """
    try:
        logger.info(f"PII detection requested for text (length: {len(request.text)})")
        
        # Get NLP manager
        nlp_manager = get_nlp_manager()
        
        # Find entities using NLP
        entities = nlp_manager.find_all_entities(
            request.text,
            use_both=request.use_both_models
        )
        
        # Get whitelist
        whitelist = set(WhitelistStorage.get_all())
        
        # Filter by whitelist
        filtered_entities = [
            {
                "text": e["text"],
                "start": e["start"],
                "end": e["end"],
                "label": e["label"],
                "source": e["source"],
                "whitelisted": e["text"] in whitelist
            }
            for e in entities
        ]
        
        return FindPIIsResponse(
            text=request.text,
            entities=filtered_entities,
            total_found=len(filtered_entities),
            whitelisted_count=sum(1 for e in filtered_entities if e["whitelisted"])
        )
        
    except Exception as e:
        logger.error(f"NLP processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"NLP processing failed: {str(e)}"
        )


@router.post(
    "/anonymize",
    response_model=AnonymizeResponse,
    summary="Anonymize text",
    description="Anonymize text using NLP and optional template"
)
async def anonymize_text(request: AnonymizeRequest):
    """
    Anonymize text using NLP detection and template-based mechanisms.
    """
    try:
        logger.info(f"Anonymization requested for text (length: {len(request.text)})")
        
        # Get template if specified
        template_data = None
        if request.template_id:
            template_data = TemplateStorage.get(request.template_id)
            if not template_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template '{request.template_id}' not found"
                )
        
        # Use default mechanism if no template
        default_mechanism = AnonymizationMechanism(type="redact")
        mechanisms_by_tag = {}
        
        if template_data:
            default_mechanism = AnonymizationMechanism(**template_data["default_mechanism"])
            mechanisms_by_tag = {
                tag: AnonymizationMechanism(**mech)
                for tag, mech in template_data.get("mechanisms_by_tag", {}).items()
            }
        
        # Get NLP manager
        nlp_manager = get_nlp_manager()
        
        # Find entities
        entities = nlp_manager.find_all_entities(request.text, use_both=True)
        
        # Get whitelist
        whitelist = set(WhitelistStorage.get_all())
        
        # Anonymize
        result = anonymizer.anonymize_text(
            text=request.text,
            entities=entities,
            default_mechanism=default_mechanism,
            mechanisms_by_tag=mechanisms_by_tag,
            whitelist=whitelist
        )
        
        return AnonymizeResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Anonymization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anonymization failed: {str(e)}"
        )
