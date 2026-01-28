"""
PDF Overlay Anonymizer - Preserves layout while anonymizing
Uses PyMuPDF to draw black rectangles over PIIs

IMPORTANT: Coordinate System Conversion
- pdfplumber: Origin at top-left, y increases downward
- PyMuPDF: Origin at bottom-left, y increases upward
- Conversion: pymupdf_y = page_height - pdfplumber_y
"""

import fitz  # PyMuPDF
import pdfplumber
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Constants
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
        output_path: str
    ) -> Dict[str, Any]:
        """
        Phase 1: Overlay anonymization (black rectangles for PIIs only, no header/footer)
        
        Args:
            pdf_path: Path to original PDF
            entities: All detected PII entities
            template: Anonymization template
            output_path: Output path for Phase 1 result
            
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
                    page_height = plumber_page.height
                    
                    # Extract words with coordinates
                    words = plumber_page.extract_words()
                    
                    # Redact PIIs (except DATEs if shifting)
                    for entity in entities:
                        mechanism = self._get_mechanism_for_entity(entity, template)
                        
                        # Skip DATE entities if mechanism is "shift" - handle in Phase 2
                        if entity["label"] == ENTITY_LABEL_DATE and mechanism.get("type") == "shift":
                            date_entities.append(entity)
                            continue
                        
                        # Redact all other entities with proper coordinate conversion
                        if self._redact_entity(fitz_page, entity, words, page_height):
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
                    page_height = plumber_page.height
                    words = plumber_page.extract_words()
                    
                    for entity in date_entities:
                        original_date = entity["text"]
                        
                        # Shift the date
                        shifted_date = date_shifter.shift_date(original_date, entity.get("groups"))
                        
                        if shifted_date and shifted_date != original_date:
                            # Find coordinates and overlay with proper conversion
                            if self._overlay_shifted_date(fitz_page, original_date, shifted_date, words, page_height):
                                shifted_count += 1
            
            # Save final result
            doc.save(output_path)
            logger.info(f"Phase 2 complete: {shifted_count} dates shifted")
            
        finally:
            doc.close()
        
        return shifted_count
    
    
    def _get_mechanism_for_entity(self, entity: Dict, template: Dict) -> Dict:
        """Get anonymization mechanism for entity from template"""
        mechanisms_by_tag = template.get("mechanismsByTag", {})
        label = entity["label"]
        
        if label in mechanisms_by_tag:
            return mechanisms_by_tag[label]
        
        return template.get("defaultMechanism", {"type": "redact"})
    
    def _redact_entity(self, page: fitz.Page, entity: Dict, words: List[Dict], page_height: float) -> bool:
        """
        Black out a single entity with proper coordinate conversion
        
        pdfplumber coordinates: origin top-left, y increases downward
        PyMuPDF coordinates: origin bottom-left, y increases upward
        
        Conversion: pymupdf_y = page_height - pdfplumber_y
        
        Args:
            page: PyMuPDF page object
            entity: Entity dict with text, label, etc.
            words: List of words from pdfplumber with coordinates
            page_height: Height of the page in pdfplumber coordinates
            
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
                
                # Calculate bounding box in pdfplumber coordinates
                x0 = min(w["x0"] for w in entity_words) - PADDING
                x1 = max(w["x1"] for w in entity_words) + PADDING
                top_plumber = min(w["top"] for w in entity_words) - PADDING
                bottom_plumber = max(w["bottom"] for w in entity_words) + PADDING
                
                # Convert to PyMuPDF coordinates (flip y-axis)
                y0 = page_height - bottom_plumber
                y1 = page_height - top_plumber
                
                # Draw black rectangle
                rect = fitz.Rect(x0, y0, x1, y1)
                page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0), width=0)
                
                logger.debug(f"Redacted '{entity_text}' at ({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f})")
                return True
        
        return False
    
    def _overlay_shifted_date(
        self,
        page: fitz.Page,
        original_date: str,
        shifted_date: str,
        words: List[Dict],
        page_height: float
    ) -> bool:
        """
        Overlay shifted date with proper coordinate conversion
        
        Args:
            page: PyMuPDF page object
            original_date: Original date string
            shifted_date: Shifted date string
            words: List of words from pdfplumber
            page_height: Height of the page in pdfplumber coordinates
            
        Returns:
            True if date was found and overlaid
        """
        for word in words:
            if word["text"] == original_date:
                # Convert coordinates from pdfplumber to PyMuPDF
                x0 = word["x0"] - PADDING
                x1 = word["x1"] + PADDING
                top_plumber = word["top"] - PADDING
                bottom_plumber = word["bottom"] + PADDING
                
                # Flip y-axis
                y0 = page_height - bottom_plumber
                y1 = page_height - top_plumber
                
                # 1. Black out original
                rect = fitz.Rect(x0, y0, x1, y1)
                page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0), width=0)
                
                # 2. Write shifted date
                font_size = bottom_plumber - top_plumber
                text_y = y1 - PADDING  # Slight offset from top
                
                page.insert_text(
                    (x0, text_y),
                    shifted_date,
                    fontsize=font_size,
                    color=(0, 0, 0),
                    fontname=DEFAULT_FONT_NAME
                )
                
                logger.debug(f"Shifted date '{original_date}' → '{shifted_date}'")
                return True
        
        return False

# Global instance
pdf_overlay_anonymizer = PDFOverlayAnonymizer()
