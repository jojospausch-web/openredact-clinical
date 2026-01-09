import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration
_default_storage = "/app/storage" if os.path.exists("/app") else "/tmp/openredact-storage"
STORAGE_DIR = Path(os.getenv("OPENREDACT_STORAGE_DIR", _default_storage))
WHITELIST_FILE = STORAGE_DIR / "whitelist.json"
TEMPLATES_FILE = STORAGE_DIR / "templates.json"

# Security limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_WHITELIST_ENTRIES = 10000
MAX_TEMPLATES = 1000


def ensure_storage_dir() -> None:
    """Create storage directory if not exists"""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Storage directory: {STORAGE_DIR}")


def load_json_file(filepath: Path, default: Any) -> Any:
    """Load JSON file with security checks"""
    try:
        if not filepath.exists():
            return default
            
        # Check file size
        if filepath.stat().st_size > MAX_FILE_SIZE:
            logger.error(f"File too large: {filepath}")
            return default
            
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return default
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return default


def save_json_file(filepath: Path, data: Any) -> bool:
    """Save data to JSON file"""
    try:
        ensure_storage_dir()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"Error saving {filepath}: {e}")
        return False


class WhitelistStorage:
    """Whitelist persistence"""

    @staticmethod
    def get_all() -> List[str]:
        """Get all whitelist entries"""
        entries = load_json_file(WHITELIST_FILE, [])
        if not isinstance(entries, list):
            logger.error("Invalid whitelist format")
            return []
        return entries[:MAX_WHITELIST_ENTRIES]

    @staticmethod
    def add(entry: str) -> bool:
        """Add whitelist entry"""
        whitelist = WhitelistStorage.get_all()
        if len(whitelist) >= MAX_WHITELIST_ENTRIES:
            logger.error(f"Whitelist limit reached: {MAX_WHITELIST_ENTRIES}")
            return False
        if entry not in whitelist:
            whitelist.append(entry)
            return save_json_file(WHITELIST_FILE, whitelist)
        return True

    @staticmethod
    def remove(entry: str) -> bool:
        """Remove whitelist entry"""
        whitelist = WhitelistStorage.get_all()
        if entry in whitelist:
            whitelist.remove(entry)
            return save_json_file(WHITELIST_FILE, whitelist)
        return True

    @staticmethod
    def set_all(entries: List[str]) -> bool:
        """Replace entire whitelist"""
        if len(entries) > MAX_WHITELIST_ENTRIES:
            logger.error(f"Too many entries: {len(entries)}")
            return False
        return save_json_file(WHITELIST_FILE, entries)


class TemplateStorage:
    """Template persistence"""

    @staticmethod
    def get_all() -> Dict[str, Dict[str, Any]]:
        """Get all templates"""
        templates = load_json_file(TEMPLATES_FILE, {})
        if not isinstance(templates, dict):
            logger.error("Invalid templates format")
            return {}
        return dict(list(templates.items())[:MAX_TEMPLATES])

    @staticmethod
    def get(template_id: str) -> Optional[Dict[str, Any]]:
        """Get single template"""
        templates = TemplateStorage.get_all()
        return templates.get(template_id)

    @staticmethod
    def save(template_id: str, template_data: Dict[str, Any]) -> bool:
        """Save template"""
        templates = TemplateStorage.get_all()
        if template_id not in templates and len(templates) >= MAX_TEMPLATES:
            logger.error(f"Template limit reached: {MAX_TEMPLATES}")
            return False
        
        # Add timestamps
        now = datetime.utcnow().isoformat()
        if template_id not in templates:
            template_data['created_at'] = now
        template_data['updated_at'] = now
        
        templates[template_id] = template_data
        return save_json_file(TEMPLATES_FILE, templates)

    @staticmethod
    def delete(template_id: str) -> bool:
        """Delete template"""
        templates = TemplateStorage.get_all()
        if template_id in templates:
            del templates[template_id]
            return save_json_file(TEMPLATES_FILE, templates)
        return True

    @staticmethod
    def import_templates(new_templates: Dict[str, Dict[str, Any]]) -> bool:
        """Import multiple templates"""
        templates = TemplateStorage.get_all()
        if len(templates) + len(new_templates) > MAX_TEMPLATES:
            logger.error("Import would exceed template limit")
            return False
        
        now = datetime.utcnow().isoformat()
        for tid, tdata in new_templates.items():
            if tid not in templates:
                tdata['created_at'] = now
            tdata['updated_at'] = now
            templates[tid] = tdata
        
        return save_json_file(TEMPLATES_FILE, templates)
