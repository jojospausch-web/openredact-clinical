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
async def test_upload_pdf():
    """Test PDF upload"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/upload-pdf",
            files={"file": ("test.pdf", SAMPLE_PDF, "application/pdf")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "pdfId" in data
        assert data["filename"] == "test.pdf"

@pytest.mark.asyncio
async def test_upload_non_pdf():
    """Test upload non-PDF file fails"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/upload-pdf",
            files={"file": ("test.txt", b"not a pdf", "text/plain")}
        )
        assert response.status_code == 400

@pytest.mark.asyncio
async def test_anonymize_pdf_flow():
    """Test complete PDF anonymization flow"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload PDF
        upload_response = await client.post(
            "/api/upload-pdf",
            files={"file": ("medical.pdf", SAMPLE_PDF, "application/pdf")}
        )
        assert upload_response.status_code == 200
        pdf_id = upload_response.json()["pdfId"]
        
        # Anonymize PDF
        anonymize_response = await client.post(
            "/api/anonymize-pdf",
            json={"pdfId": pdf_id}
        )
        assert anonymize_response.status_code == 200
        anon_pdf_id = anonymize_response.json()["anonymizedPdfId"]
        
        # Download anonymized PDF
        download_response = await client.get(f"/api/download-pdf/{anon_pdf_id}")
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "application/pdf"

@pytest.mark.asyncio
async def test_list_pdfs():
    """Test listing PDFs"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/pdfs")
        assert response.status_code == 200
        data = response.json()
        assert "pdfs" in data
        assert "total" in data

@pytest.mark.asyncio
async def test_delete_pdf():
    """Test PDF deletion"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload
        upload_response = await client.post(
            "/api/upload-pdf",
            files={"file": ("test.pdf", SAMPLE_PDF, "application/pdf")}
        )
        pdf_id = upload_response.json()["pdfId"]
        
        # Delete
        delete_response = await client.delete(f"/api/pdf/{pdf_id}")
        assert delete_response.status_code == 200
        
        # Verify deleted
        download_response = await client.get(f"/api/download-pdf/{pdf_id}")
        assert download_response.status_code == 404
