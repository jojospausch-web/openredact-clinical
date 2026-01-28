"""
PDF Overlay Anonymizer - Preserves layout while anonymizing
Uses PyMuPDF to draw black rectangles over PIIs
"""

import fitz  # PyMuPDF
import pdfplumber
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Constants
HEADER_REGION_PERCENTAGE = 0.20  # Top 20% of page
FOOTER_REGION_PERCENTAGE = 0.90  # Bottom 10% of page (starts at 90%)
DEFAULT_FONT_NAME = "helv"  # Helvetica font
ENTITY_LABEL_DATE = "DATE"
PADDING = 2  # Pixels of padding around redacted text

class PDFOverlayAnonymizer:
    """Anonymize PDF by overlaying black rectangles while preserving layout"""
    
    def anonymize_pdf_hybrid(
        self,
        pdf_path: str,
        entities: List[Dict[str, Any]],
        template: Dict[str, Any],
        output_path: str,
        redact_header: bool = True,
        redact_footer: bool = True
    ) -> Dict[str, Any]:
        """
        Phase 1: Overlay anonymization (black rectangles for non-date PIIs)
        
        Args:
            pdf_path: Path to original PDF
            entities: All detected PII entities
            template: Anonymization template
            output_path: Output path for Phase 1 result
            redact_header: Black out header region (top 20%)
            redact_footer: Black out footer region (bottom 10%)
            
        Returns:
            dict with statistics and date entities for Phase 2
        """
        doc = fitz.open(pdf_path)
        date_entities = []
        redacted_count = 0
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, plumber_page in enumerate(pdf.pages):
                    if page_num >= len(doc):
                        break
                        
                    fitz_page = doc[page_num]
                    
                    # 1. Redact header (logos, letterhead)
                    if redact_header:
                        self._redact_header_region(fitz_page, plumber_page)
                        logger.info(f"Page {page_num}: Header redacted")
                    
                    # 2. Redact footer (phone table, banking info)
                    if redact_footer:
                        self._redact_footer_region(fitz_page, plumber_page)
                        logger.info(f"Page {page_num}: Footer redacted")
                    
                    # 3. Extract words with coordinates
                    words = plumber_page.extract_words()
                    
                    # 4. Redact PIIs (except DATEs if shifting)
                    for entity in entities:
                        mechanism = self._get_mechanism_for_entity(entity, template)
                        
                        # Skip DATE entities if mechanism is "shift" - handle in Phase 2
                        if entity["label"] == ENTITY_LABEL_DATE and mechanism.get("type") == "shift":
                            date_entities.append(entity)
                            continue
                        
                        # Redact all other entities
                        if self._redact_entity(fitz_page, entity, words):
                            redacted_count += 1
            
            # Save Phase 1 result
            doc.save(output_path)
            logger.info(f"Phase 1 complete: {redacted_count} entities redacted, {len(date_entities)} dates for Phase 2")
            
        finally:
            doc.close()
        
        return {
            "redacted_count": redacted_count,
            "date_entities": date_entities,
            "phase1_path": output_path
        }
    
    def overlay_shifted_dates(
        self,
        pdf_path: str,
        date_entities: List[Dict[str, Any]],
        shift_months: int,
        shift_days: int,
        output_path: str
    ) -> int:
        """
        Phase 2: Overlay shifted dates on top of original dates
        
        Args:
            pdf_path: PDF from Phase 1 (with redacted non-date PIIs)
            date_entities: Only DATE entities
            shift_months: Months to shift
            shift_days: Days to shift
            output_path: Final output path
            
        Returns:
            Number of dates shifted
        """
        from app.date_shifter import DateShifter
        
        date_shifter = DateShifter(shift_months=shift_months, shift_days=shift_days)
        doc = fitz.open(pdf_path)
        shifted_count = 0
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, plumber_page in enumerate(pdf.pages):
                    if page_num >= len(doc):
                        break
                        
                    fitz_page = doc[page_num]
                    words = plumber_page.extract_words()
                    
                    for entity in date_entities:
                        original_date = entity["text"]
                        
                        # Shift the date
                        shifted_date = date_shifter.shift_date(original_date, entity.get("groups"))
                        
                        if shifted_date and shifted_date != original_date:
                            # Find coordinates and overlay
                            if self._overlay_shifted_date(fitz_page, original_date, shifted_date, words):
                                shifted_count += 1
            
            # Save final result
            doc.save(output_path)
            logger.info(f"Phase 2 complete: {shifted_count} dates shifted")
            
        finally:
            doc.close()
        
        return shifted_count
    
    def _redact_header_region(self, page: fitz.Page, plumber_page):
        """Black out header region (top 20% of page)"""
        page_height = plumber_page.height
        page_width = plumber_page.width
        
        # Header = top portion (logos, certifications, letterhead)
        header_rect = fitz.Rect(0, 0, page_width, page_height * HEADER_REGION_PERCENTAGE)
        
        # Draw black rectangle
        page.draw_rect(header_rect, color=(0, 0, 0), fill=(0, 0, 0), width=0)
    
    def _redact_footer_region(self, page: fitz.Page, plumber_page):
        """Black out footer region (bottom 10% of page)"""
        page_height = plumber_page.height
        page_width = plumber_page.width
        
        # Footer = bottom portion
        footer_rect = fitz.Rect(0, page_height * FOOTER_REGION_PERCENTAGE, page_width, page_height)
        
        # Draw black rectangle
        page.draw_rect(footer_rect, color=(0, 0, 0), fill=(0, 0, 0), width=0)
    
    def _get_mechanism_for_entity(self, entity: Dict, template: Dict) -> Dict:
        """Get anonymization mechanism for entity from template"""
        mechanisms_by_tag = template.get("mechanismsByTag", {})
        label = entity["label"]
        
        if label in mechanisms_by_tag:
            return mechanisms_by_tag[label]
        
        return template.get("defaultMechanism", {"type": "redact"})
    
    def _redact_entity(self, page: fitz.Page, entity: Dict, words: List[Dict]) -> bool:
        """
        Black out a single entity
        
        Returns:
            True if entity was found and redacted
        """
        entity_text = entity["text"]
        
        # Find matching word(s) in PDF
        for i, word in enumerate(words):
            if word["text"] in entity_text or entity_text in word["text"]:
                # Found start of entity
                entity_words = [word]
                
                # Handle multi-word entities
                remaining_text = entity_text.replace(word["text"], "", 1).strip()
                j = i + 1
                
                while remaining_text and j < len(words):
                    next_word = words[j]
                    if next_word["text"] in remaining_text:
                        entity_words.append(next_word)
                        remaining_text = remaining_text.replace(next_word["text"], "", 1).strip()
                    j += 1
                
                # Calculate bounding box
                x0 = min(w["x0"] for w in entity_words) - PADDING
                x1 = max(w["x1"] for w in entity_words) + PADDING
                top = min(w["top"] for w in entity_words) - PADDING
                bottom = max(w["bottom"] for w in entity_words) + PADDING
                
                # Draw black rectangle
                rect = fitz.Rect(x0, top, x1, bottom)
                page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0), width=0)
                
                return True
        
        return False
    
    def _overlay_shifted_date(
        self,
        page: fitz.Page,
        original_date: str,
        shifted_date: str,
        words: List[Dict]
    ) -> bool:
        """
        Overlay shifted date on top of original date
        
        Returns:
            True if date was found and overlaid
        """
        for word in words:
            if word["text"] == original_date:
                # 1. Black out original date
                rect = fitz.Rect(
                    word["x0"] - PADDING,
                    word["top"] - PADDING,
                    word["x1"] + PADDING,
                    word["bottom"] + PADDING
                )
                page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0), width=0)
                
                # 2. Estimate font size
                font_size = word["bottom"] - word["top"]
                
                # 3. Insert shifted date text
                page.insert_text(
                    (word["x0"], word["bottom"] - PADDING),
                    shifted_date,
                    fontsize=font_size,
                    color=(0, 0, 0),
                    fontname=DEFAULT_FONT_NAME
                )
                
                return True
        
        return False

# Global instance
pdf_overlay_anonymizer = PDFOverlayAnonymizer()
