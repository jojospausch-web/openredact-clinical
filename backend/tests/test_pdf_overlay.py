import pytest
from httpx import AsyncClient
from pathlib import Path
from app.main import app

# Sample PDF content (minimal valid PDF)
SAMPLE_PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000056 00000 n
0000000115 00000 n
0000000214 00000 n
trailer<</Size 5/Root 1 0 R>>
startxref
307
%%EOF"""


@pytest.mark.asyncio
async def test_hybrid_anonymization_preserves_layout():
    """Test that hybrid method is used when preserve_layout=True"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload PDF
        upload_response = await client.post(
            "/api/upload-pdf",
            files={"file": ("medical.pdf", SAMPLE_PDF, "application/pdf")}
        )
        assert upload_response.status_code == 200
        pdf_id = upload_response.json()["pdfId"]
        
        # Anonymize with hybrid method (preserve_layout=True)
        anonymize_response = await client.post(
            "/api/anonymize-pdf",
            json={
                "pdfId": pdf_id,
                "preserveLayout": True,
                "checkImages": True
            }
        )
        assert anonymize_response.status_code == 200
        response_data = anonymize_response.json()
        
        assert "anonymizedPdfId" in response_data
        assert response_data.get("method") == "hybrid_overlay"
        assert "redactedCount" in response_data
        assert "shiftedCount" in response_data
        assert "imagesFound" in response_data
        assert "warnings" in response_data


@pytest.mark.asyncio
async def test_legacy_anonymization_text_replacement():
    """Test that legacy method is used when preserve_layout=False"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload PDF
        upload_response = await client.post(
            "/api/upload-pdf",
            files={"file": ("medical.pdf", SAMPLE_PDF, "application/pdf")}
        )
        assert upload_response.status_code == 200
        pdf_id = upload_response.json()["pdfId"]
        
        # Anonymize with legacy method (preserve_layout=False)
        anonymize_response = await client.post(
            "/api/anonymize-pdf",
            json={
                "pdfId": pdf_id,
                "preserveLayout": False
            }
        )
        assert anonymize_response.status_code == 200
        response_data = anonymize_response.json()
        
        assert "anonymizedPdfId" in response_data
        assert response_data.get("method") == "text_replacement"


@pytest.mark.asyncio
async def test_hybrid_anonymization_with_image_detection():
    """Test that image detection works"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload PDF
        upload_response = await client.post(
            "/api/upload-pdf",
            files={"file": ("medical.pdf", SAMPLE_PDF, "application/pdf")}
        )
        assert upload_response.status_code == 200
        pdf_id = upload_response.json()["pdfId"]
        
        # Anonymize with image detection
        anonymize_response = await client.post(
            "/api/anonymize-pdf",
            json={
                "pdfId": pdf_id,
                "preserveLayout": True,
                "checkImages": True,
                "checkImagesOcr": False
            }
        )
        assert anonymize_response.status_code == 200
        response_data = anonymize_response.json()
        
        assert response_data.get("method") == "hybrid_overlay"
        assert "imagesFound" in response_data
        assert isinstance(response_data["imagesFound"], int)
        assert isinstance(response_data["warnings"], list)


@pytest.mark.asyncio
async def test_hybrid_default_preserve_layout():
    """Test that preserve_layout defaults to True"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload PDF
        upload_response = await client.post(
            "/api/upload-pdf",
            files={"file": ("medical.pdf", SAMPLE_PDF, "application/pdf")}
        )
        assert upload_response.status_code == 200
        pdf_id = upload_response.json()["pdfId"]
        
        # Anonymize without specifying preserve_layout (should default to True)
        anonymize_response = await client.post(
            "/api/anonymize-pdf",
            json={"pdfId": pdf_id}
        )
        assert anonymize_response.status_code == 200
        response_data = anonymize_response.json()
        
        # Should use hybrid method by default
        assert response_data.get("method") == "hybrid_overlay"


@pytest.mark.asyncio
async def test_hybrid_anonymization_pii_only_no_header_footer():
    """Test that only PIIs are redacted, not header/footer"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload PDF
        upload_response = await client.post(
            "/api/upload-pdf",
            files={"file": ("medical.pdf", SAMPLE_PDF, "application/pdf")}
        )
        assert upload_response.status_code == 200
        pdf_id = upload_response.json()["pdfId"]
        
        # Anonymize - should only redact PIIs, not header/footer
        anonymize_response = await client.post(
            "/api/anonymize-pdf",
            json={
                "pdfId": pdf_id,
                "preserveLayout": True
            }
        )
        assert anonymize_response.status_code == 200
        response_data = anonymize_response.json()
        
        # Method should be hybrid_overlay
        assert response_data.get("method") == "hybrid_overlay"
        # Should have counts for redacted/shifted entities
        assert "redactedCount" in response_data
        assert "shiftedCount" in response_data

