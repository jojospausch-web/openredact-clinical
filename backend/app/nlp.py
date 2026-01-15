"""
NLP Manager for German clinical text analysis using spaCy and Stanza.
"""
import logging
import re
from typing import List, Dict, Any, Set
import spacy
import stanza
from spacy.tokens import Doc
from app.pii_patterns import regex_detector
from app.blacklist_manager import blacklist_manager

logger = logging.getLogger(__name__)


class NLPManager:
    """Manages NLP models for German clinical text analysis"""
    
    def __init__(self):
        """Initialize spaCy and Stanza models"""
        try:
            # Load spaCy German model
            logger.info("Loading spaCy German model...")
            self.spacy_nlp = spacy.load("de_core_news_sm")
            logger.info("spaCy model loaded successfully")
        except OSError as e:
            logger.error(f"Failed to load spaCy model: {e}")
            logger.info("Attempting to download de_core_news_sm...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "de_core_news_sm"], check=True)
            self.spacy_nlp = spacy.load("de_core_news_sm")
        
        # Try to load Stanza German model (optional)
        self.stanza_nlp = None
        try:
            logger.info("Loading Stanza German model...")
            self.stanza_nlp = stanza.Pipeline(
                "de", 
                processors="tokenize,ner",
                download_method=None  # Don't auto-download
            )
            logger.info("Stanza model loaded successfully")
        except Exception as e:
            logger.warning(f"Stanza model not available: {e}")
            logger.warning("Continuing with spaCy only. Install Stanza models manually if needed.")
        
    def find_entities_spacy(self, text: str) -> List[Dict[str, Any]]:
        """Find entities using spaCy"""
        doc = self.spacy_nlp(text)
        entities = []
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "start": ent.start_char,
                "end": ent.end_char,
                "label": ent.label_,
                "source": "spacy"
            })
        return entities
    
    def find_entities_stanza(self, text: str) -> List[Dict[str, Any]]:
        """Find entities using Stanza"""
        if self.stanza_nlp is None:
            logger.warning("Stanza model not available, skipping")
            return []
        
        doc = self.stanza_nlp(text)
        entities = []
        for sentence in doc.sentences:
            for ent in sentence.ents:
                entities.append({
                    "text": ent.text,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "label": ent.type,
                    "source": "stanza"
                })
        return entities
    
    def find_all_entities(self, text: str, use_both: bool = True) -> List[Dict[str, Any]]:
        """
        Find entities using blacklist, regex, and NLP models.
        
        Detection order (by priority):
        1. BLACKLIST - Highest priority, always detected and anonymized
        2. Regex patterns - Structured data (titles, emails, dates, etc.)
        3. spaCy NLP - German NER model
        4. Stanza NLP - Optional secondary German NER model
        
        Deduplication prefers blacklist entities over longer spans.
        """
        entities = []
        
        # 1. BLACKLIST CHECK FIRST (highest priority!)
        blacklist_entities = self._find_blacklisted_terms(text)
        entities.extend(blacklist_entities)
        
        # 2. Regex-based detection (titles, structured data)
        regex_entities = regex_detector.find_all(text)
        entities.extend(regex_entities)
        
        # 3. spaCy entities
        entities.extend(self.find_entities_spacy(text))
        
        # 4. Stanza entities (if enabled)
        if use_both and self.stanza_nlp is not None:
            entities.extend(self.find_entities_stanza(text))
        
        # 5. Deduplicate overlapping entities
        entities = self._deduplicate_entities(entities)
        
        return entities
    
    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate/overlapping entities, prefer blacklist, then longer spans"""
        if not entities:
            return []
        
        # Sort by priority:
        # 1. Blacklist entities first (highest priority)
        # 2. Then by start position
        # 3. Then by length (longest first)
        def sort_key(e):
            is_blacklist = 1 if e.get("source") == "blacklist" else 0
            return (-is_blacklist, e["start"], -(e["end"] - e["start"]))
        
        sorted_entities = sorted(entities, key=sort_key)
        
        deduplicated = []
        for entity in sorted_entities:
            # Check if overlaps with existing entities
            overlaps = False
            for existing in deduplicated:
                if self._entities_overlap(entity, existing):
                    overlaps = True
                    break
            
            if not overlaps:
                deduplicated.append(entity)
        
        return deduplicated
    
    def _entities_overlap(self, e1: Dict, e2: Dict) -> bool:
        """Check if two entities overlap"""
        return not (e1["end"] <= e2["start"] or e2["end"] <= e1["start"])
    
    def _find_blacklisted_terms(self, text: str) -> List[Dict[str, Any]]:
        """Find all blacklisted terms in text"""
        entities = []
        blacklist = blacklist_manager.get_all()
        
        for term in blacklist:
            # Find all occurrences (case-insensitive)
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            for match in pattern.finditer(text):
                entities.append({
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "label": "BLACKLISTED",
                    "source": "blacklist",
                    "whitelisted": False  # Blacklist overrides whitelist!
                })
        
        return entities
    
    def is_whitelisted(self, entity_text: str, whitelist: List[str]) -> bool:
        """
        Smart whitelist matching:
        - Exact match: "NYHA" in whitelist matches "NYHA"
        - Word match: "NYHA" in whitelist matches "NYHA IV"
        - Partial match: "Charité" in whitelist matches "Charité Berlin"
        """
        # 1. Exact match
        if entity_text in whitelist:
            return True
        
        # 2. Word-based matching (for "NYHA IV" when "NYHA" is whitelisted)
        entity_words = entity_text.split()
        for word in entity_words:
            if word in whitelist:
                return True
        
        # 3. Partial match (for "Charité Berlin" when "Charité" is whitelisted)
        for whitelisted_term in whitelist:
            if whitelisted_term in entity_text:
                return True
        
        return False


# Global instance (initialized lazily)
_nlp_manager = None


def get_nlp_manager() -> NLPManager:
    """Get or create the global NLP manager instance"""
    global _nlp_manager
    if _nlp_manager is None:
        _nlp_manager = NLPManager()
    return _nlp_manager
