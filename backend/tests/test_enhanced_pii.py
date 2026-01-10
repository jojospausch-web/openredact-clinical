"""
Integration tests for enhanced PII detection (phone, email, dates, date-shifting).
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestPhoneEmailAnonymization:
    """Test that phone numbers and emails are detected and anonymized"""
    
    def test_phone_anonymization(self):
        """Test phone number detection and anonymization"""
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Kontakt: 030-12345678"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Phone should be anonymized
        assert "030-12345678" not in data["anonymizedText"]
        assert data["entitiesFound"] >= 1
    
    def test_email_anonymization(self):
        """Test email detection and anonymization"""
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Kontakt: max.mustermann@email.de"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Email should be anonymized
        assert "max.mustermann@email.de" not in data["anonymizedText"]
        assert data["entitiesFound"] >= 1
    
    def test_phone_and_email_together(self):
        """Test that both phone and email are detected together"""
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Kontakt: max.mustermann@email.de, Tel: 030-12345678"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Both should be anonymized
        assert "030-12345678" not in data["anonymizedText"]
        assert "max.mustermann@email.de" not in data["anonymizedText"]
        assert data["entitiesFound"] >= 2


class TestDateShiftingIntegration:
    """Test date shifting mechanism in full anonymization flow"""
    
    def test_date_shifting_basic(self):
        """Test basic date shifting"""
        # Create template with date shifting
        template_response = client.post(
            "/api/templates/date-shift-test",
            json={
                "name": "Date Shift Template",
                "defaultMechanism": {"type": "redact"},
                "mechanismsByTag": {
                    "DATE": {
                        "type": "shift",
                        "shiftMonths": 28,
                        "shiftDays": 0
                    }
                }
            }
        )
        assert template_response.status_code == 201
        
        # Anonymize with date shifting
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Aufnahme am 15.03.2024",
                "templateId": "date-shift-test"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Original date should be gone
        assert "15.03.2024" not in data["anonymizedText"]
        
        # Should contain shifted date (15.07.2026 = 28 months later)
        assert "15.07.2026" in data["anonymizedText"]
    
    def test_date_shifting_preserves_temporal_relations(self):
        """Test that temporal relationships are preserved"""
        # Create template with date shifting
        client.post(
            "/api/templates/date-shift-preserve",
            json={
                "name": "Date Shift Preserve Template",
                "defaultMechanism": {"type": "redact"},
                "mechanismsByTag": {
                    "DATE": {
                        "type": "shift",
                        "shiftMonths": 6,
                        "shiftDays": 0
                    }
                }
            }
        )
        
        # Anonymize text with two dates
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Aufnahme am 15.03.2024, Entlassung am 20.03.2024",
                "templateId": "date-shift-preserve"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Original dates should be gone
        assert "15.03.2024" not in data["anonymizedText"]
        assert "20.03.2024" not in data["anonymizedText"]
        
        # Should contain shifted dates (both shifted by 6 months)
        # 15.03.2024 + 6 months = 15.09.2024
        # 20.03.2024 + 6 months = 20.09.2024
        assert "15.09.2024" in data["anonymizedText"]
        assert "20.09.2024" in data["anonymizedText"]
    
    def test_date_shifting_with_days(self):
        """Test date shifting with day offset"""
        # Create template with day shifting
        client.post(
            "/api/templates/date-shift-days",
            json={
                "name": "Date Shift Days Template",
                "defaultMechanism": {"type": "redact"},
                "mechanismsByTag": {
                    "DATE": {
                        "type": "shift",
                        "shiftMonths": 0,
                        "shiftDays": 100
                    }
                }
            }
        )
        
        # Anonymize with day shifting
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Termin am 01.01.2024",
                "templateId": "date-shift-days"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Original date should be gone
        assert "01.01.2024" not in data["anonymizedText"]
        
        # Should contain shifted date (01.01.2024 + 100 days = 10.04.2024)
        assert "10.04.2024" in data["anonymizedText"]


class TestUserTestCase:
    """Test the exact case from user feedback"""
    
    def test_complete_medical_text(self):
        """Test complete medical text with all PII types"""
        text = (
            "Der Patient wohnt in Berlin, Musterstraße 123, 10115 Berlin. "
            "Kontakt: max.mustermann@email.de, Tel: 030-12345678."
        )
        
        response = client.post(
            "/api/anonymize",
            json={"text": text}
        )
        assert response.status_code == 200
        data = response.json()
        
        # ALL PIIs must be anonymized
        anonymized = data["anonymizedText"]
        assert "10115" not in anonymized  # ZIP
        assert "max.mustermann@email.de" not in anonymized  # Email
        assert "030-12345678" not in anonymized  # Phone
        
        # Should have found multiple entities
        assert data["entitiesFound"] >= 3
    
    def test_user_example_exact(self):
        """Test exact example from user's problem statement"""
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Tel: 030-12345678, Email: max@example.de"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Both phone and email should be redacted
        anonymized = data["anonymizedText"]
        assert "030-12345678" not in anonymized
        assert "max@example.de" not in anonymized
        
        # Should have found at least 2 entities
        assert data["entitiesFound"] >= 2


class TestFindPIIsEndpoint:
    """Test the /find-piis endpoint with new regex patterns"""
    
    def test_find_phones_and_emails(self):
        """Test that find-piis detects phones and emails"""
        response = client.post(
            "/api/find-piis",
            json={
                "text": "Kontakt: test@email.de, Tel: 030-12345678",
                "useBothModels": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should find both email and phone
        entity_labels = [e["label"] for e in data["entities"]]
        assert "EMAIL" in entity_labels
        assert "PHONE" in entity_labels
    
    def test_find_dates(self):
        """Test that find-piis detects dates"""
        response = client.post(
            "/api/find-piis",
            json={
                "text": "Geboren am 15.03.2024",
                "useBothModels": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should find date
        entity_labels = [e["label"] for e in data["entities"]]
        assert "DATE" in entity_labels
    
    def test_find_zipcodes(self):
        """Test that find-piis detects postal codes"""
        response = client.post(
            "/api/find-piis",
            json={
                "text": "Wohnort: 10115 Berlin",
                "useBothModels": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should find zipcode
        entity_labels = [e["label"] for e in data["entities"]]
        assert "ZIPCODE" in entity_labels


class TestMixedContent:
    """Test handling of mixed content (NLP + regex entities)"""
    
    def test_nlp_and_regex_together(self):
        """Test that NLP entities (names, locations) work with regex entities"""
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Patient Max Mustermann, Tel: 030-123456, wohnt in 10115 Berlin"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should anonymize both NLP entities (Max Mustermann, Berlin) 
        # and regex entities (phone, zipcode)
        anonymized = data["anonymizedText"]
        assert "030-123456" not in anonymized
        assert "10115" not in anonymized
        
        # Should have found multiple entities
        assert data["entitiesFound"] >= 2


class TestAnonymizationMechanisms:
    """Test different mechanisms with new entity types"""
    
    def test_hash_mechanism_with_phone(self):
        """Test hash mechanism with phone numbers"""
        # Create template with hash
        client.post(
            "/api/templates/hash-phone",
            json={
                "name": "Hash Phone Template",
                "defaultMechanism": {"type": "redact"},
                "mechanismsByTag": {
                    "PHONE": {"type": "hash"}
                }
            }
        )
        
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Tel: 030-12345678",
                "templateId": "hash-phone"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should contain hash
        assert "[HASH:" in data["anonymizedText"]
        assert "030-12345678" not in data["anonymizedText"]
    
    def test_replace_mechanism_with_email(self):
        """Test replace mechanism with emails"""
        # Create template with replace
        client.post(
            "/api/templates/replace-email",
            json={
                "name": "Replace Email Template",
                "defaultMechanism": {"type": "redact"},
                "mechanismsByTag": {
                    "EMAIL": {"type": "replace", "replacement": "[EMAIL_REMOVED]"}
                }
            }
        )
        
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Email: test@example.de",
                "templateId": "replace-email"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should contain custom replacement
        assert "[EMAIL_REMOVED]" in data["anonymizedText"]
        assert "test@example.de" not in data["anonymizedText"]
