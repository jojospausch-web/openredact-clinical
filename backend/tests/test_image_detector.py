"""
Tests for Image Detector module
"""
import pytest
from pathlib import Path
from app.image_detector import image_detector


def test_image_detector_initialization():
    """Test that image detector initializes properly"""
    assert image_detector is not None
    # OCR availability depends on whether tesseract is installed
    assert isinstance(image_detector.ocr_available, bool)


def test_detect_images_no_images(tmp_path):
    """Test detection on PDF without images"""
    # Create a simple PDF without images
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((100, 100), "Test document without images")
    
    pdf_path = tmp_path / "no_images.pdf"
    doc.save(str(pdf_path))
    doc.close()
    
    # Detect images
    result = image_detector.detect_images(str(pdf_path))
    
    assert result["total_images"] == 0
    assert len(result["images_by_page"]) == 0
    assert len(result["warnings"]) == 0


def test_detect_images_with_images(tmp_path):
    """Test detection on PDF with embedded images"""
    # Create a simple PDF with an embedded image
    import fitz
    from PIL import Image
    import io
    
    # Create a simple image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    # Create PDF with image
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, 150, 150)
    page.insert_image(rect, stream=img_bytes.read())
    
    pdf_path = tmp_path / "with_images.pdf"
    doc.save(str(pdf_path))
    doc.close()
    
    # Detect images
    result = image_detector.detect_images(str(pdf_path))
    
    assert result["total_images"] == 1
    assert 1 in result["images_by_page"]
    assert result["images_by_page"][1] == 1
    assert len(result["warnings"]) > 0
    assert "ACHTUNG" in result["warnings"][0]


def test_check_images_for_text_no_tesseract():
    """Test OCR check when Tesseract is not available"""
    if not image_detector.ocr_available:
        result = image_detector.check_images_for_text("dummy.pdf")
        assert result["images_with_text"] == 0
        assert len(result["warnings"]) > 0
        assert "OCR nicht verfügbar" in result["warnings"][0]


@pytest.mark.skipif(
    not image_detector.ocr_available,
    reason="Tesseract OCR not available"
)
def test_check_images_for_text_with_tesseract(tmp_path):
    """Test OCR check when Tesseract is available"""
    # This test requires Tesseract to be installed
    # It will be skipped if Tesseract is not available
    
    # Create a simple PDF without images for testing
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((100, 100), "Test")
    
    pdf_path = tmp_path / "test_ocr.pdf"
    doc.save(str(pdf_path))
    doc.close()
    
    result = image_detector.check_images_for_text(str(pdf_path))
    
    # Should complete without error
    assert "images_with_text" in result
    assert "image_details" in result
    assert "warnings" in result


def test_warning_messages_format():
    """Test that warning messages are properly formatted"""
    import fitz
    from PIL import Image
    import io
    
    # Create a temporary PDF with multiple images
    doc = fitz.open()
    page1 = doc.new_page()
    page2 = doc.new_page()
    
    # Add images to both pages
    img = Image.new('RGB', (50, 50), color='blue')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_data = img_bytes.getvalue()
    
    rect = fitz.Rect(10, 10, 60, 60)
    page1.insert_image(rect, stream=img_data)
    page1.insert_image(rect, stream=img_data)  # 2 images on page 1
    page2.insert_image(rect, stream=img_data)  # 1 image on page 2
    
    # Save to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        doc.save(tmp.name)
        doc.close()
        
        # Detect images
        result = image_detector.detect_images(tmp.name)
        
        assert result["total_images"] == 3
        assert result["images_by_page"][1] == 2
        assert result["images_by_page"][2] == 1
        
        # Check warning format
        warnings = result["warnings"]
        assert len(warnings) >= 4
        assert "3 Bild(er)" in warnings[0]
        assert "NICHT anonymisiert" in warnings[1]
        assert "Manuelle Prüfung" in warnings[2]
        assert "Seite 1" in warnings[3]
        assert "Seite 2" in warnings[3]
        
        # Cleanup
        import os
        os.unlink(tmp.name)
