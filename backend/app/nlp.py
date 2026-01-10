"""
NLP Manager for German clinical text analysis using spaCy and Stanza.
"""
import logging
from typing import List, Dict, Any, Set
import spacy
import stanza
from spacy.tokens import Doc
from app.pii_patterns import regex_detector

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
        """Find entities using NLP AND regex patterns"""
        entities = []
        
        # 1. Regex-based detection FIRST (titles, structured data)
        regex_entities = regex_detector.find_all(text)
        entities.extend(regex_entities)
        
        # 2. spaCy entities
        entities.extend(self.find_entities_spacy(text))
        
        # 3. Stanza entities (if enabled)
        if use_both and self.stanza_nlp is not None:
            entities.extend(self.find_entities_stanza(text))
        
        # 4. Deduplicate overlapping entities
        entities = self._deduplicate_entities(entities)
        
        return entities
    
    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate/overlapping entities, prefer longer spans"""
        if not entities:
            return []
        
        # Sort by start position, then by length (longest first)
        sorted_entities = sorted(
            entities,
            key=lambda e: (e["start"], -(e["end"] - e["start"]))
        )
        
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


# Global instance (initialized lazily)
_nlp_manager = None


def get_nlp_manager() -> NLPManager:
    """Get or create the global NLP manager instance"""
    global _nlp_manager
    if _nlp_manager is None:
        _nlp_manager = NLPManager()
    return _nlp_manager
