"""
Tests for regex-based PII detection patterns and date shifting.
"""
import pytest
from app.pii_patterns import regex_detector
from app.date_shifter import DateShifter
from datetime import datetime


class TestPhoneDetection:
    """Test phone number detection"""
    
    def test_landline_detection(self):
        """Test landline phone number detection"""
        text = "Kontakt: 030-12345678"
        entities = regex_detector.find_phones(text)
        
        assert len(entities) == 1
        assert entities[0]["label"] == "PHONE"
        assert entities[0]["text"] == "030-12345678"
    
    def test_mobile_detection(self):
        """Test mobile phone number detection"""
        text = "Mobil: 0170-9876543"
        entities = regex_detector.find_phones(text)
        
        assert len(entities) == 1
        assert entities[0]["text"] == "0170-9876543"
    
    def test_international_format(self):
        """Test international format phone numbers"""
        text = "Tel: +49 30 123456"
        entities = regex_detector.find_phones(text)
        
        assert len(entities) == 1
        assert "+49 30 123456" in entities[0]["text"]
    
    def test_multiple_phones(self):
        """Test detection of multiple phone numbers"""
        text = "Kontakt: 030-12345678, Mobil: 0170-9876543, Tel: +49 30 123456"
        entities = regex_detector.find_phones(text)
        
        assert len(entities) == 3
        assert all(e["label"] == "PHONE" for e in entities)


class TestEmailDetection:
    """Test email address detection"""
    
    def test_simple_email(self):
        """Test simple email detection"""
        text = "Email: max.mustermann@example.de"
        entities = regex_detector.find_emails(text)
        
        assert len(entities) == 1
        assert entities[0]["label"] == "EMAIL"
        assert entities[0]["text"] == "max.mustermann@example.de"
    
    def test_email_with_umlauts(self):
        """Test email detection with German umlauts"""
        text = "Email: müller@klinik.com"
        entities = regex_detector.find_emails(text)
        
        assert len(entities) == 1
        assert entities[0]["text"] == "müller@klinik.com"
    
    def test_multiple_emails(self):
        """Test detection of multiple emails"""
        text = "Email: max.mustermann@example.de, müller@klinik.com"
        entities = regex_detector.find_emails(text)
        
        assert len(entities) == 2


class TestDateDetection:
    """Test date detection"""
    
    def test_german_dot_format(self):
        """Test German DD.MM.YYYY format"""
        text = "Geboren am 15.03.2024"
        entities = regex_detector.find_dates(text)
        
        assert len(entities) == 1
        assert entities[0]["text"] == "15.03.2024"
        assert entities[0]["label"] == "DATE"
    
    def test_slash_format(self):
        """Test DD/MM/YYYY format"""
        text = "Termin: 01/12/2023"
        entities = regex_detector.find_dates(text)
        
        assert len(entities) == 1
        assert entities[0]["text"] == "01/12/2023"
    
    def test_iso_format(self):
        """Test ISO YYYY-MM-DD format"""
        text = "Datum: 2024-12-31"
        entities = regex_detector.find_dates(text)
        
        assert len(entities) == 1
        assert entities[0]["text"] == "2024-12-31"
    
    def test_multiple_date_formats(self):
        """Test multiple date formats in one text"""
        text = "Geboren am 15.03.2024, Termin: 01/12/2023, Datum: 2024-12-31"
        entities = regex_detector.find_dates(text)
        
        assert len(entities) == 3
        assert entities[0]["text"] == "15.03.2024"
        assert entities[1]["text"] == "01/12/2023"
        assert entities[2]["text"] == "2024-12-31"


class TestZipcodeDetection:
    """Test postal code detection"""
    
    def test_simple_zipcode(self):
        """Test simple postal code detection"""
        text = "Wohnort: 10115 Berlin"
        entities = regex_detector.find_zipcodes(text)
        
        assert len(entities) == 1
        assert entities[0]["text"] == "10115"
        assert entities[0]["label"] == "ZIPCODE"
    
    def test_multiple_zipcodes(self):
        """Test multiple postal codes"""
        text = "Wohnort: 10115 Berlin, PLZ: 20095"
        entities = regex_detector.find_zipcodes(text)
        
        assert len(entities) == 2
        assert entities[0]["text"] == "10115"
        assert entities[1]["text"] == "20095"
    
    def test_excludes_all_zeros(self):
        """Test that 00000 is not detected"""
        text = "Code: 00000"
        entities = regex_detector.find_zipcodes(text)
        
        assert len(entities) == 0
    
    def test_excludes_sequential(self):
        """Test that sequential numbers are excluded"""
        text = "Number: 12345"
        entities = regex_detector.find_zipcodes(text)
        
        # 12345 should be excluded as sequential
        assert len(entities) == 0


class TestIBANDetection:
    """Test IBAN detection"""
    
    def test_iban_detection(self):
        """Test IBAN number detection"""
        text = "IBAN: DE89370400440532013000"
        entities = regex_detector.find_ibans(text)
        
        assert len(entities) == 1
        assert entities[0]["label"] == "IBAN"
        assert "DE" in entities[0]["text"]
    
    def test_iban_with_spaces(self):
        """Test IBAN with spaces"""
        text = "IBAN: DE89 3704 0044 0532 0130 00"
        entities = regex_detector.find_ibans(text)
        
        assert len(entities) == 1


class TestTitleDetection:
    """Test medical title detection"""
    
    def test_dr_title(self):
        """Test Dr. title detection"""
        text = "Behandelt von Dr. Schmidt"
        entities = regex_detector.find_titles(text)
        
        assert len(entities) >= 1
        assert any("Schmidt" in e["text"] for e in entities)
        assert all(e["label"] == "PERSON" for e in entities)
    
    def test_prof_title(self):
        """Test Prof. title detection"""
        text = "Prof. Müller führte die Operation durch"
        entities = regex_detector.find_titles(text)
        
        assert len(entities) >= 1
        assert any("Müller" in e["text"] for e in entities)
    
    def test_dr_med_title(self):
        """Test Dr. med. title detection"""
        text = "Dr. med. Wagner ist der Chefarzt"
        entities = regex_detector.find_titles(text)
        
        assert len(entities) >= 1
        assert any("Wagner" in e["text"] for e in entities)


class TestDateShifting:
    """Test date shifting mechanism"""
    
    def test_shift_months_forward(self):
        """Test shifting months forward"""
        shifter = DateShifter(shift_months=28, shift_days=0)
        
        # 15.03.2024 + 28 months = 15.07.2026
        result = shifter.shift_date("15.03.2024")
        assert result == "15.07.2026"
    
    def test_shift_months_backward(self):
        """Test shifting months backward"""
        shifter = DateShifter(shift_months=-12)
        
        # 15.03.2024 - 12 months = 15.03.2023
        result = shifter.shift_date("15.03.2024")
        assert result == "15.03.2023"
    
    def test_shift_days(self):
        """Test shifting days"""
        shifter = DateShifter(shift_months=0, shift_days=10)
        
        # 15.03.2024 + 10 days = 25.03.2024
        result = shifter.shift_date("15.03.2024")
        assert result == "25.03.2024"
    
    def test_shift_preserves_format_dot(self):
        """Test that shifting preserves dot format"""
        shifter = DateShifter(shift_months=6)
        result = shifter.shift_date("15.03.2024")
        
        # Should still use dot format
        assert "." in result
    
    def test_shift_preserves_format_slash(self):
        """Test that shifting preserves slash format"""
        shifter = DateShifter(shift_months=6)
        result = shifter.shift_date("15/03/2024")
        
        # Should still use slash format
        assert "/" in result
    
    def test_shift_preserves_format_iso(self):
        """Test that shifting preserves ISO format"""
        shifter = DateShifter(shift_months=6)
        result = shifter.shift_date("2024-03-15")
        
        # Should still use ISO format (YYYY-MM-DD)
        assert result.startswith("20")
        assert "-" in result
    
    def test_shift_handles_month_overflow(self):
        """Test shifting handles month overflow correctly"""
        shifter = DateShifter(shift_months=1)
        
        # Jan 31 + 1 month should give last day of Feb
        result = shifter.shift_date("31.01.2024")
        # 2024 is leap year, so Feb has 29 days
        assert result == "29.02.2024"
    
    def test_temporal_relationship_preserved(self):
        """Test that temporal relationships are preserved"""
        shifter = DateShifter(shift_months=6)
        
        admission = shifter.shift_date("15.03.2024")
        discharge = shifter.shift_date("20.03.2024")
        
        # Parse dates
        adm_date = datetime.strptime(admission, '%d.%m.%Y')
        dis_date = datetime.strptime(discharge, '%d.%m.%Y')
        
        # Difference should still be 5 days
        assert (dis_date - adm_date).days == 5


class TestFindAll:
    """Test finding all PIIs at once"""
    
    def test_find_all_entities(self):
        """Test finding all entities in complex text"""
        text = """
        Patient: Max Mustermann
        Geboren: 15.03.1985
        Wohnort: 10115 Berlin
        Tel: 030-12345678
        Email: max@example.de
        """
        
        entities = regex_detector.find_all(text)
        
        # Should find date, zipcode, phone, email
        labels = [e["label"] for e in entities]
        assert "DATE" in labels
        assert "ZIPCODE" in labels
        assert "PHONE" in labels
        assert "EMAIL" in labels
    
    def test_find_all_preserves_positions(self):
        """Test that positions are correctly preserved"""
        text = "Email: test@example.de, Tel: 030-123456"
        entities = regex_detector.find_all(text)
        
        # Check that we can extract entities using positions
        for entity in entities:
            extracted = text[entity["start"]:entity["end"]]
            assert extracted == entity["text"]
