"""
Anonymization engine for text based on detected entities and templates.
"""
import logging
import hashlib
from typing import List, Dict, Any, Set, Optional
from pydantic import BaseModel
from app.date_shifter import DateShifter

logger = logging.getLogger(__name__)


class AnonymizationMechanism(BaseModel):
    """Anonymization mechanism configuration"""
    type: str  # redact, replace, hash, partial, mask
    replacement: Optional[str] = None


class Anonymizer:
    """Handles text anonymization based on detected entities and templates"""
    
    def anonymize_text(
        self,
        text: str,
        entities: List[Dict[str, Any]],
        default_mechanism: AnonymizationMechanism,
        mechanisms_by_tag: Dict[str, AnonymizationMechanism] = None,
        whitelist: Set[str] = None
    ) -> Dict[str, Any]:
        """Anonymize text based on entities and mechanisms"""
        
        if mechanisms_by_tag is None:
            mechanisms_by_tag = {}
        
        if whitelist is None:
            whitelist = set()
        
        # Filter entities by whitelist
        filtered_entities = [
            e for e in entities 
            if e["text"] not in whitelist
        ]
        
        # Sort entities by position (reverse order for safe replacement)
        sorted_entities = sorted(
            filtered_entities,
            key=lambda e: e["start"],
            reverse=True
        )
        
        # Apply anonymization
        anonymized_text = text
        replacements = []
        
        for entity in sorted_entities:
            # Get mechanism for this entity type
            mechanism = mechanisms_by_tag.get(
                entity["label"],
                default_mechanism
            )
            
            # Apply mechanism
            replacement = self._apply_mechanism(
                entity["text"],
                mechanism,
                entity_data=entity
            )
            
            # Replace in text
            start = entity["start"]
            end = entity["end"]
            anonymized_text = (
                anonymized_text[:start] + 
                replacement + 
                anonymized_text[end:]
            )
            
            replacements.append({
                "original": entity["text"],
                "replacement": replacement,
                "start": start,
                "end": end,
                "label": entity["label"],
                "mechanism": mechanism.type
            })
        
        return {
            "original_text": text,
            "anonymized_text": anonymized_text,
            "entities_found": len(filtered_entities),
            "entities_anonymized": len(replacements),
            "replacements": replacements
        }
    
    def _apply_mechanism(
        self,
        text: str,
        mechanism: AnonymizationMechanism,
        entity_data: Dict[str, Any] = None
    ) -> str:
        """Apply anonymization mechanism to text"""
        
        if mechanism.type == "redact":
            return "[REDACTED]"
        
        elif mechanism.type == "replace":
            return mechanism.replacement or "[REDACTED]"
        
        elif mechanism.type == "hash":
            # MD5 hash (deterministic, same text → same hash)
            hash_obj = hashlib.md5(text.encode())
            return f"[HASH:{hash_obj.hexdigest()[:8]}]"
        
        elif mechanism.type == "partial":
            # Keep first/last char, redact middle
            if len(text) <= 2:
                return text[0] + "*"
            return text[0] + "*" * (len(text) - 2) + text[-1]
        
        elif mechanism.type == "mask":
            # Replace with asterisks
            return "*" * len(text)
        
        elif mechanism.type == "shift":
            # Date shifting
            if entity_data and entity_data.get("label") == "DATE":
                shifter = DateShifter(
                    shift_months=getattr(mechanism, 'shift_months', None) or 0,
                    shift_days=getattr(mechanism, 'shift_days', None) or 0
                )
                date_groups = entity_data.get("groups")
                return shifter.shift_date(text, date_groups)
            else:
                # Not a date, redact instead
                return "[REDACTED]"
        
        else:
            # Default: redact
            return "[REDACTED]"


# Global instance
anonymizer = Anonymizer()
