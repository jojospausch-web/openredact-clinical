"""
Image Detector - Finds images in PDFs and optionally checks for text/PIIs

Detects embedded images in PDF documents and can optionally use OCR
to extract and analyze text within those images.
"""

import fitz  # PyMuPDF
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ImageDetector:
    """Detect images in PDFs and check for embedded text"""
    
    def __init__(self):
        # Check if Tesseract OCR is available
        self.ocr_available = False
        try:
            import pytesseract
            self.pytesseract = pytesseract
            self.ocr_available = True
            logger.info("Tesseract OCR available")
        except ImportError:
            logger.warning("Tesseract not installed, OCR disabled")
    
    def detect_images(self, pdf_path: str) -> Dict[str, Any]:
        """
        Detect all images in PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            {
                "total_images": 5,
                "images_by_page": {1: 3, 3: 2},
                "warnings": [...]
            }
        """
        doc = fitz.open(pdf_path)
        images_by_page = {}
        total_images = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            
            if image_list:
                images_by_page[page_num + 1] = len(image_list)
                total_images += len(image_list)
                logger.info(f"Page {page_num+1}: {len(image_list)} images found")
        
        doc.close()
        
        warnings = []
        if total_images > 0:
            warnings.append(f"⚠️  ACHTUNG: {total_images} Bild(er) im PDF gefunden!")
            warnings.append("Bilder wurden NICHT anonymisiert.")
            warnings.append("Manuelle Prüfung erforderlich!")
            
            page_info = ", ".join([
                f"Seite {p} ({c} Bild{'er' if c > 1 else ''})" 
                for p, c in images_by_page.items()
            ])
            warnings.append(f"Bilder befinden sich auf: {page_info}")
        
        return {
            "total_images": total_images,
            "images_by_page": images_by_page,
            "warnings": warnings
        }
    
    def check_images_for_text(self, pdf_path: str) -> Dict[str, Any]:
        """
        Check images for embedded text using OCR
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            {
                "images_with_text": 2,
                "image_details": [...],
                "warnings": [...]
            }
        """
        if not self.ocr_available:
            return {
                "images_with_text": 0,
                "image_details": [],
                "warnings": ["OCR nicht verfügbar (Tesseract nicht installiert)"]
            }
        
        from PIL import Image
        import io
        from app.nlp import get_nlp_manager
        
        nlp = get_nlp_manager()
        doc = fitz.open(pdf_path)
        image_details = []
        images_with_text = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                
                try:
                    # Extract image
                    img_info = doc.extract_image(xref)
                    image_bytes = img_info["image"]
                    
                    # OCR
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    text = self.pytesseract.image_to_string(pil_image, lang='deu')
                    
                    if text.strip():
                        # Check for PIIs
                        entities = nlp.find_all_entities(text)
                        
                        if entities:
                            images_with_text += 1
                            image_details.append({
                                "page": page_num + 1,
                                "imageIndex": img_index + 1,
                                "textFound": text[:200],  # First 200 chars
                                "piisDetected": list(set(e["label"] for e in entities)),
                                "piiCount": len(entities)
                            })
                            logger.warning(
                                f"PIIs found in image: Page {page_num+1}, "
                                f"Image {img_index+1}, {len(entities)} PIIs"
                            )
                
                except Exception as e:
                    logger.error(f"OCR failed for image on page {page_num+1}: {e}")
        
        doc.close()
        
        warnings = []
        if images_with_text > 0:
            warnings.append(f"🚨 KRITISCH: {images_with_text} Bild(er) enthalten TEXT!")
            for detail in image_details:
                warnings.append(
                    f"Seite {detail['page']}, Bild {detail['imageIndex']}: "
                    f"{detail['piiCount']} PIIs gefunden ({', '.join(detail['piisDetected'])})"
                )
            warnings.append("⚠️  Bilder wurden NICHT anonymisiert!")
            warnings.append("Manuelle Schwärzung der Bilder zwingend erforderlich!")
        
        return {
            "images_with_text": images_with_text,
            "image_details": image_details,
            "warnings": warnings
        }


# Global instance
image_detector = ImageDetector()
