from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid
import os
import PyPDF2
import pdfplumber
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Configuration - use same pattern as storage.py
_default_storage = "/app/storage" if os.path.exists("/app") else "/tmp/openredact-storage"
STORAGE_DIR = Path(os.getenv("OPENREDACT_STORAGE_DIR", _default_storage))
PDF_STORAGE_DIR = STORAGE_DIR / "pdfs"

class PDFManager:
    """Handles PDF upload, storage, text extraction, and generation"""
    
    def __init__(self, storage_dir: Path = PDF_STORAGE_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata storage
        self.metadata_file = self.storage_dir / "metadata.json"
        
    def save_uploaded_pdf(
        self,
        file_content: bytes,
        filename: str,
        max_size_mb: int = 50
    ) -> Dict[str, Any]:
        """Save uploaded PDF and extract metadata"""
        
        # Validate file size
        size_mb = len(file_content) / (1024 * 1024)
        if size_mb > max_size_mb:
            raise ValueError(f"File too large: {size_mb:.2f}MB (max {max_size_mb}MB)")
        
        # Validate PDF format
        if not self._is_valid_pdf(file_content):
            raise ValueError("Invalid PDF file")
        
        # Generate unique ID
        pdf_id = str(uuid.uuid4())
        
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        
        # Save file
        pdf_path = self.storage_dir / f"{pdf_id}_{safe_filename}"
        pdf_path.write_bytes(file_content)
        
        # Extract text
        text = self.extract_text(pdf_path)
        
        # Save metadata
        metadata = {
            "id": pdf_id,
            "original_filename": safe_filename,
            "file_path": str(pdf_path),
            "file_size_bytes": len(file_content),
            "file_size_mb": round(size_mb, 2),
            "uploaded_at": datetime.utcnow().isoformat(),
            "text_length": len(text),
            "status": "uploaded"
        }
        
        self._save_metadata(pdf_id, metadata)
        
        return {
            "pdf_id": pdf_id,
            "filename": safe_filename,
            "file_size_mb": round(size_mb, 2),
            "text_preview": text[:500] if text else "",
            "text_length": len(text)
        }
    
    def extract_text(self, pdf_path: Path) -> str:
        """Extract text from PDF using PyPDF2 with pdfplumber fallback"""
        
        text = ""
        
        # Try PyPDF2 first (faster)
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            if text.strip():
                logger.info(f"Extracted {len(text)} chars using PyPDF2")
                return text.strip()
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {e}, trying pdfplumber")
        
        # Fallback to pdfplumber (better for complex PDFs)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            logger.info(f"Extracted {len(text)} chars using pdfplumber")
            return text.strip()
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return ""
    
    def generate_anonymized_pdf(
        self,
        original_pdf_id: str,
        anonymized_text: str
    ) -> Dict[str, Any]:
        """Generate new PDF with anonymized text using wkhtmltopdf"""
        
        # Get original metadata
        original_metadata = self._get_metadata(original_pdf_id)
        if not original_metadata:
            raise ValueError(f"PDF {original_pdf_id} not found")
        
        # Generate new PDF ID
        new_pdf_id = str(uuid.uuid4())
        
        # Create HTML from anonymized text
        html_content = self._text_to_html(
            anonymized_text,
            title=f"Anonymized - {original_metadata['original_filename']}"
        )
        
        # Temporary HTML file
        html_path = self.storage_dir / f"{new_pdf_id}_temp.html"
        html_path.write_text(html_content, encoding='utf-8')
        
        # Output PDF path
        output_filename = f"anonymized_{original_metadata['original_filename']}"
        output_path = self.storage_dir / f"{new_pdf_id}_{output_filename}"
        
        # Generate PDF using wkhtmltopdf
        import subprocess
        try:
            subprocess.run([
                'wkhtmltopdf',
                '--encoding', 'UTF-8',
                '--page-size', 'A4',
                '--margin-top', '20mm',
                '--margin-bottom', '20mm',
                '--margin-left', '15mm',
                '--margin-right', '15mm',
                str(html_path),
                str(output_path)
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"wkhtmltopdf failed: {e.stderr.decode()}")
            raise ValueError("PDF generation failed")
        finally:
            # Cleanup temp HTML
            if html_path.exists():
                html_path.unlink()
        
        # Save metadata
        metadata = {
            "id": new_pdf_id,
            "original_filename": output_filename,
            "file_path": str(output_path),
            "file_size_bytes": output_path.stat().st_size,
            "file_size_mb": round(output_path.stat().st_size / (1024 * 1024), 2),
            "created_at": datetime.utcnow().isoformat(),
            "original_pdf_id": original_pdf_id,
            "status": "anonymized"
        }
        
        self._save_metadata(new_pdf_id, metadata)
        
        return {
            "pdf_id": new_pdf_id,
            "filename": output_filename,
            "file_size_mb": metadata["file_size_mb"]
        }
    
    def get_pdf_path(self, pdf_id: str) -> Optional[Path]:
        """Get file path for PDF ID"""
        metadata = self._get_metadata(pdf_id)
        if metadata:
            path = Path(metadata["file_path"])
            if path.exists():
                return path
        return None
    
    def delete_pdf(self, pdf_id: str) -> bool:
        """Delete PDF and metadata"""
        metadata = self._get_metadata(pdf_id)
        if not metadata:
            return False
        
        # Delete file
        path = Path(metadata["file_path"])
        if path.exists():
            path.unlink()
        
        # Delete metadata
        self._delete_metadata(pdf_id)
        return True
    
    def list_pdfs(self) -> List[Dict[str, Any]]:
        """List all PDFs"""
        metadata = self._load_all_metadata()
        return list(metadata.values())
    
    # === Helper Methods ===
    
    def _is_valid_pdf(self, content: bytes) -> bool:
        """Check if content is valid PDF"""
        return content.startswith(b'%PDF-')
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Remove path components
        filename = Path(filename).name
        # Remove special characters
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        sanitized = "".join(c if c in safe_chars else "_" for c in filename)
        # Ensure .pdf extension
        if not sanitized.lower().endswith('.pdf'):
            sanitized += '.pdf'
        return sanitized
    
    def _text_to_html(self, text: str, title: str = "Anonymized Document") -> str:
        """Convert text to formatted HTML for PDF generation"""
        # Escape HTML
        import html
        escaped_text = html.escape(text)
        
        # Convert newlines to <br>
        formatted_text = escaped_text.replace('\n', '<br>')
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{html.escape(title)}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
        }}
        .header {{
            border-bottom: 2px solid #ccc;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .content {{
            white-space: pre-wrap;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{html.escape(title)}</h1>
        <p>Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>
    <div class="content">
        {formatted_text}
    </div>
</body>
</html>
"""
    
    def _save_metadata(self, pdf_id: str, metadata: Dict[str, Any]):
        """Save metadata for PDF"""
        all_metadata = self._load_all_metadata()
        all_metadata[pdf_id] = metadata
        
        import json
        self.metadata_file.write_text(json.dumps(all_metadata, indent=2))
    
    def _get_metadata(self, pdf_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for PDF"""
        all_metadata = self._load_all_metadata()
        return all_metadata.get(pdf_id)
    
    def _delete_metadata(self, pdf_id: str):
        """Delete metadata for PDF"""
        all_metadata = self._load_all_metadata()
        if pdf_id in all_metadata:
            del all_metadata[pdf_id]
            import json
            self.metadata_file.write_text(json.dumps(all_metadata, indent=2))
    
    def _load_all_metadata(self) -> Dict[str, Any]:
        """Load all PDF metadata"""
        if not self.metadata_file.exists():
            return {}
        
        import json
        try:
            return json.loads(self.metadata_file.read_text())
        except:
            return {}

# Global instance
pdf_manager = PDFManager()
