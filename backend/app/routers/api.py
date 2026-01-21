"""
API Router - All API endpoints with NLP integration
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse

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
    # PDF schemas
    UploadPDFResponse,
    AnonymizePDFRequest,
    AnonymizePDFResponse,
    ListPDFsResponse,
)
from app.storage import WhitelistStorage, TemplateStorage
from app.blacklist_manager import blacklist_manager
from app.nlp import get_nlp_manager
from app.anonymizer import anonymizer
from app.pdf_manager import pdf_manager

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


# ===== BLACKLIST ENDPOINTS =====

@router.get(
    "/blacklist",
    response_model=WhitelistResponse,
    summary="Get all blacklist entries"
)
async def get_blacklist():
    """Retrieve all blacklist entries"""
    entries = blacklist_manager.get_all()
    return WhitelistResponse(entries=entries)


@router.post(
    "/blacklist",
    response_model=SuccessResponse,
    summary="Add blacklist entry",
    status_code=status.HTTP_201_CREATED
)
async def add_blacklist_entry(entry: WhitelistEntry):
    """Add new entry to blacklist (force anonymization)"""
    success = blacklist_manager.add_entry(entry.entry)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Entry already exists or limit exceeded"
        )
    return SuccessResponse(success=True, message="Entry added")


@router.delete(
    "/blacklist/{entry}",
    response_model=SuccessResponse,
    summary="Remove blacklist entry"
)
async def remove_blacklist_entry(entry: str):
    """Remove entry from blacklist"""
    success = blacklist_manager.remove_entry(entry)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found"
        )
    return SuccessResponse(success=True, message="Entry removed")


@router.put(
    "/blacklist",
    response_model=SuccessResponse,
    summary="Replace entire blacklist"
)
async def update_blacklist(bulk: WhitelistBulkUpdate):
    """Replace all blacklist entries"""
    success = blacklist_manager.set_all(bulk.entries)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update blacklist (limit exceeded or storage error)"
        )
    return SuccessResponse(success=True, message=f"Blacklist updated with {len(bulk.entries)} entries")


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
        whitelist = WhitelistStorage.get_all()
        
        # Apply smart whitelist matching
        filtered_entities = [
            {
                "text": e["text"],
                "start": e["start"],
                "end": e["end"],
                "label": e["label"],
                "source": e["source"],
                "whitelisted": (
                    # Blacklisted items can never be whitelisted
                    e.get("source") != "blacklist" and 
                    nlp_manager.is_whitelisted(e["text"], whitelist)
                )
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


# ===== PDF ENDPOINTS =====

@router.post("/upload-pdf", response_model=UploadPDFResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload PDF and extract text"""
    
    # Validate content type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be PDF format"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        # Save and process
        result = pdf_manager.save_uploaded_pdf(
            file_content=content,
            filename=file.filename or "document.pdf"
        )
        
        return UploadPDFResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF processing failed: {str(e)}"
        )

@router.post("/anonymize-pdf", response_model=AnonymizePDFResponse)
async def anonymize_pdf(request: AnonymizePDFRequest):
    """
    Anonymize PDF with optional layout preservation
    
    - preserve_layout=False: Text replacement (current method, loses layout)
    - preserve_layout=True: Hybrid overlay (preserves layout, blacks out PIIs, shifts dates)
    """
    
    try:
        # Determine which anonymization method to use
        if request.preserve_layout:
            # Use hybrid overlay method
            anon_pdf_id = await pdf_manager.anonymize_pdf_hybrid(
                request.pdf_id,
                request.template_id or "medical",
                redact_header=request.redact_header,
                redact_footer=request.redact_footer
            )
            
            # Get metadata for response
            metadata = pdf_manager._get_metadata(anon_pdf_id)
            
            return AnonymizePDFResponse(
                anonymized_pdf_id=anon_pdf_id,
                original_pdf_id=request.pdf_id,
                filename=metadata["original_filename"],
                file_size_mb=metadata["file_size_mb"],
                entities_found=metadata.get("redacted_count", 0) + metadata.get("shifted_count", 0),
                entities_anonymized=metadata.get("redacted_count", 0) + metadata.get("shifted_count", 0),
                method="hybrid_overlay",
                redacted_count=metadata.get("redacted_count", 0),
                shifted_count=metadata.get("shifted_count", 0)
            )
        else:
            # Use legacy text replacement method
            # Get PDF path
            pdf_path = pdf_manager.get_pdf_path(request.pdf_id)
            if not pdf_path:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"PDF {request.pdf_id} not found"
                )
            
            # Extract text
            text = pdf_manager.extract_text(pdf_path)
            if not text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not extract text from PDF"
                )
            
            # Get template if specified
            template_data = None
            if request.template_id:
                template_data = TemplateStorage.get(request.template_id)
                if not template_data:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Template '{request.template_id}' not found"
                    )
            
            # Prepare anonymization
            default_mechanism = AnonymizationMechanism(type="redact")
            mechanisms_by_tag = {}
            
            if template_data:
                default_mechanism = AnonymizationMechanism(**template_data["default_mechanism"])
                mechanisms_by_tag = {
                    tag: AnonymizationMechanism(**mech)
                    for tag, mech in template_data.get("mechanisms_by_tag", {}).items()
                }
            
            # Find entities
            nlp_manager = get_nlp_manager()
            entities = nlp_manager.find_all_entities(text, use_both=True)
            
            # Get whitelist
            whitelist = set(WhitelistStorage.get_all())
            
            # Anonymize text
            anonymization_result = anonymizer.anonymize_text(
                text=text,
                entities=entities,
                default_mechanism=default_mechanism,
                mechanisms_by_tag=mechanisms_by_tag,
                whitelist=whitelist
            )
            
            # Generate new PDF
            pdf_result = pdf_manager.generate_anonymized_pdf(
                original_pdf_id=request.pdf_id,
                anonymized_text=anonymization_result["anonymized_text"]
            )
            
            return AnonymizePDFResponse(
                anonymized_pdf_id=pdf_result["pdf_id"],
                original_pdf_id=request.pdf_id,
                filename=pdf_result["filename"],
                file_size_mb=pdf_result["file_size_mb"],
                entities_found=anonymization_result["entities_found"],
                entities_anonymized=anonymization_result["entities_anonymized"],
                method="text_replacement"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF anonymization failed: {str(e)}"
        )

@router.get("/download-pdf/{pdf_id}")
async def download_pdf(pdf_id: str):
    """Download PDF by ID"""
    
    pdf_path = pdf_manager.get_pdf_path(pdf_id)
    if not pdf_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF {pdf_id} not found"
        )
    
    metadata = pdf_manager._get_metadata(pdf_id)
    filename = metadata.get("original_filename", "document.pdf")
    
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=filename
    )

@router.delete("/pdf/{pdf_id}", response_model=SuccessResponse)
async def delete_pdf(pdf_id: str):
    """Delete PDF"""
    
    success = pdf_manager.delete_pdf(pdf_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF {pdf_id} not found"
        )
    
    return SuccessResponse(success=True, message="PDF deleted")

@router.get("/pdfs", response_model=ListPDFsResponse)
async def list_pdfs():
    """List all uploaded/anonymized PDFs"""
    
    pdfs = pdf_manager.list_pdfs()
    return ListPDFsResponse(pdfs=pdfs, total=len(pdfs))
