"""
Regex-based PII detector for German medical documents.
Detects structured PIIs like phone numbers, emails, dates, postal codes, etc.
"""
import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class RegexPIIDetector:
    """Detects structured PIIs using regex patterns (German medical context)"""
    
    # German phone number patterns
    PHONE_PATTERNS = [
        # International: +49 170 1234567, +49-170-1234567
        r'\+49[\s-]?\d{2,4}[\s-]?\d{6,9}\b',
        # Landline with separator: 030-12345678, 030/12345678, 030 12345678
        r'\b0\d{2,3}[\s/-]\d{6,10}\b',
        # Mobile without separator: 01701234567
        r'\b0\d{9,11}\b',
    ]
    
    # Email patterns (with German umlauts)
    EMAIL_PATTERN = r'\b[A-Za-z0-9äöüÄÖÜß._%+-]+@[A-Za-z0-9äöüÄÖÜß.-]+\.[A-Za-z]{2,}\b'
    
    # German date patterns
    DATE_PATTERNS = [
        # DD.MM.YYYY, DD.MM.YY
        r'\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b',
        # DD/MM/YYYY, DD-MM-YYYY
        r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',
        # YYYY-MM-DD (ISO)
        r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b',
    ]
    
    # German postal codes
    ZIPCODE_PATTERN = r'\b\d{5}\b'
    
    # IBAN (German)
    IBAN_PATTERN = r'\bDE\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2}\b'
    
    # Medical titles (FIXED for multi-title combinations!)
    TITLE_PATTERNS = [
        # Multi-title combinations (Prof. Dr. Name, Dr. Prof. Name)
        r'\b(Prof\.\s+Dr\.|Dr\.\s+Prof\.)\s+(?:med\.\s+)?([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)\b',
        
        # Single title with med. (Dr. med. Name, Prof. med. Name)
        r'\b(Dr\.|Prof\.|PD)\s+med\.\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)\b',
        
        # Single title (Dr. Name, Prof. Name)
        r'\b(Dr\.|Prof\.)\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)\b',
        
        # Dipl.-Med.
        r'\bDipl\.-Med\.\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)\b',
    ]
    
    def __init__(self):
        # Compile patterns for performance
        self.phone_regex = [re.compile(p) for p in self.PHONE_PATTERNS]
        self.email_regex = re.compile(self.EMAIL_PATTERN)
        self.date_regex = [re.compile(p) for p in self.DATE_PATTERNS]
        self.zipcode_regex = re.compile(self.ZIPCODE_PATTERN)
        self.iban_regex = re.compile(self.IBAN_PATTERN)
        self.title_regex = [re.compile(p) for p in self.TITLE_PATTERNS]
    
    def find_phones(self, text: str) -> List[Dict[str, Any]]:
        """Find phone numbers"""
        entities = []
        for regex in self.phone_regex:
            for match in regex.finditer(text):
                entities.append({
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "label": "PHONE",
                    "source": "regex"
                })
        return entities
    
    def find_emails(self, text: str) -> List[Dict[str, Any]]:
        """Find email addresses"""
        entities = []
        for match in self.email_regex.finditer(text):
            entities.append({
                "text": match.group(),
                "start": match.start(),
                "end": match.end(),
                "label": "EMAIL",
                "source": "regex"
            })
        return entities
    
    def find_dates(self, text: str) -> List[Dict[str, Any]]:
        """Find dates in various formats"""
        entities = []
        for regex in self.date_regex:
            for match in regex.finditer(text):
                entities.append({
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "label": "DATE",
                    "source": "regex",
                    "groups": match.groups()  # For date parsing
                })
        return entities
    
    def find_zipcodes(self, text: str) -> List[Dict[str, Any]]:
        """Find German postal codes (5 digits)"""
        entities = []
        for match in self.zipcode_regex.finditer(text):
            # Validate it's likely a ZIP (not just any 5 digits)
            # Check if preceded/followed by location context
            zipcode = match.group()
            
            # Simple heuristic: not all zeros, not sequential
            if zipcode != "00000" and not self._is_sequential(zipcode):
                entities.append({
                    "text": zipcode,
                    "start": match.start(),
                    "end": match.end(),
                    "label": "ZIPCODE",
                    "source": "regex"
                })
        return entities
    
    def find_ibans(self, text: str) -> List[Dict[str, Any]]:
        """Find IBAN numbers"""
        entities = []
        for match in self.iban_regex.finditer(text):
            entities.append({
                "text": match.group(),
                "start": match.start(),
                "end": match.end(),
                "label": "IBAN",
                "source": "regex"
            })
        return entities
    
    def find_titles(self, text: str) -> List[Dict[str, Any]]:
        """Find medical titles + names (Dr. Schmidt, Prof. Müller)"""
        entities = []
        for regex in self.title_regex:
            for match in regex.finditer(text):
                entities.append({
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "label": "PERSON",
                    "source": "regex_title"
                })
        return entities
    
    def find_all(self, text: str) -> List[Dict[str, Any]]:
        """Find all regex-based PIIs"""
        entities = []
        
        # Order matters: titles first (to catch "Dr. Name" as one entity)
        entities.extend(self.find_titles(text))
        entities.extend(self.find_phones(text))
        entities.extend(self.find_emails(text))
        entities.extend(self.find_dates(text))
        entities.extend(self.find_zipcodes(text))
        entities.extend(self.find_ibans(text))
        
        return entities
    
    def _is_sequential(self, s: str) -> bool:
        """Check if string is sequential (12345, etc.)"""
        if len(s) < 3:
            return False
        diffs = [int(s[i+1]) - int(s[i]) for i in range(len(s)-1)]
        return all(d == diffs[0] for d in diffs)


# Global instance
regex_detector = RegexPIIDetector()
