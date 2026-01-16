"""
Blacklist Manager - Terms that should ALWAYS be anonymized.
"""
import json
from pathlib import Path
from typing import List, Set
import logging
import os

logger = logging.getLogger(__name__)

# Configuration
_default_storage = "/app/storage" if os.path.exists("/app") else "/tmp/openredact-storage"
STORAGE_DIR = Path(os.getenv("OPENREDACT_STORAGE_DIR", _default_storage))
BLACKLIST_FILE = STORAGE_DIR / "blacklist.json"

# Security limit
MAX_BLACKLIST_ENTRIES = 10000


class BlacklistManager:
    """Manages blacklisted terms that should ALWAYS be anonymized"""
    
    def __init__(self, storage_path: Path = BLACKLIST_FILE):
        self.storage_path = storage_path
        self.blacklist: Set[str] = set()
        self._load()
    
    def _load(self):
        """Load blacklist from file"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        # Legacy format support (just a list) - for backward compatibility
                        # TODO: Remove in future version after migration period
                        self.blacklist = set(data)
                    else:
                        # Current format with metadata
                        self.blacklist = set(data.get("blacklist", []))
                logger.info(f"Loaded {len(self.blacklist)} blacklist entries")
            except Exception as e:
                logger.error(f"Failed to load blacklist: {e}")
                self.blacklist = set()
        else:
            logger.info("No blacklist file found, starting with empty blacklist")
    
    def _save(self):
        """Save blacklist to file"""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({"blacklist": list(self.blacklist)}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save blacklist: {e}")
    
    def add_entry(self, term: str) -> bool:
        """Add term to blacklist. Returns False if already exists or limit exceeded."""
        if term in self.blacklist:
            return False  # Already exists
        if len(self.blacklist) >= MAX_BLACKLIST_ENTRIES:
            logger.error(f"Blacklist limit reached: {MAX_BLACKLIST_ENTRIES}")
            return False
        self.blacklist.add(term)
        self._save()
        logger.info(f"Added to blacklist: {term}")
        return True
    
    def remove_entry(self, term: str) -> bool:
        """Remove term from blacklist. Returns False if not found."""
        if term not in self.blacklist:
            return False  # Not found
        self.blacklist.discard(term)
        self._save()
        logger.info(f"Removed from blacklist: {term}")
        return True
    
    def get_all(self) -> List[str]:
        """Get all blacklisted terms"""
        return sorted(list(self.blacklist))
    
    def set_all(self, terms: List[str]) -> bool:
        """Replace entire blacklist. Returns False if limit exceeded."""
        if len(terms) > MAX_BLACKLIST_ENTRIES:
            logger.error(f"Too many entries: {len(terms)}")
            return False
        self.blacklist = set(terms)
        self._save()
        logger.info(f"Blacklist replaced with {len(terms)} entries")
        return True
    
    def is_blacklisted(self, term: str) -> bool:
        """Check if term is blacklisted"""
        return term in self.blacklist


# Global instance
blacklist_manager = BlacklistManager()
