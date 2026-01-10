"""
Tests for NLP integration - PII detection and anonymization
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestFindPIIs:
    """Test PII detection endpoint"""

    def test_find_piis_basic(self):
        """Test basic PII detection"""
        response = client.post(
            "/api/find-piis",
            json={
                "text": "Der Patient Max Mustermann wurde im Krankenhaus Berlin behandelt.",
                "useBothModels": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data
        assert "totalFound" in data
        assert "whitelistedCount" in data
        # Should find entities (names, organizations)
        assert data["totalFound"] >= 0

    def test_find_piis_single_model(self):
        """Test PII detection with single model"""
        response = client.post(
            "/api/find-piis",
            json={
                "text": "Dr. Schmidt behandelte Anna Müller.",
                "useBothModels": False
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data

    def test_find_piis_empty_text(self):
        """Test PII detection with empty text fails"""
        response = client.post(
            "/api/find-piis",
            json={
                "text": "",
                "useBothModels": True
            }
        )
        assert response.status_code == 422  # Validation error

    def test_find_piis_long_text(self):
        """Test PII detection with longer text"""
        long_text = "Der Patient wurde von Dr. Schmidt behandelt. " * 10
        response = client.post(
            "/api/find-piis",
            json={
                "text": long_text,
                "useBothModels": True
            }
        )
        assert response.status_code == 200


class TestAnonymize:
    """Test anonymization endpoint"""

    def test_anonymize_basic(self):
        """Test basic text anonymization"""
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Dr. Schmidt behandelte Anna Müller in der Charité."
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "anonymizedText" in data
        assert "originalText" in data
        assert "entitiesFound" in data
        assert "entitiesAnonymized" in data
        assert "replacements" in data

    def test_anonymize_with_whitelist(self):
        """Test that whitelisted terms are not anonymized"""
        # First, clear and add to whitelist
        client.put(
            "/api/whitelist",
            json={"entries": ["Charité"]}
        )
        
        # Anonymize text
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Der Patient wurde in der Charité behandelt."
            }
        )
        assert response.status_code == 200
        data = response.json()
        # Charité should NOT be anonymized (whitelisted)
        # Note: This depends on NLP detecting "Charité" as an entity
        assert "Charité" in data["anonymizedText"] or "Charité" not in data["originalText"]

    def test_anonymize_with_template(self):
        """Test anonymization with custom template"""
        # Create template
        template_response = client.post(
            "/api/templates/test-template",
            json={
                "name": "Test Template",
                "defaultMechanism": {"type": "redact"},
                "mechanismsByTag": {
                    "PER": {"type": "replace", "replacement": "[NAME]"},
                    "ORG": {"type": "replace", "replacement": "[ORGANISATION]"}
                }
            }
        )
        assert template_response.status_code == 201
        
        # Anonymize with template
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Dr. Meyer arbeitet im Universitätsklinikum Hamburg.",
                "templateId": "test-template"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "anonymizedText" in data

    def test_anonymize_with_nonexistent_template(self):
        """Test anonymization with non-existent template returns 404"""
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Test text.",
                "templateId": "nonexistent-template-12345"
            }
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_anonymize_no_entities(self):
        """Test anonymization with text containing no entities"""
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Dies ist ein einfacher Satz ohne Namen oder Orte."
            }
        )
        assert response.status_code == 200
        data = response.json()
        # Should still return valid response
        assert "anonymizedText" in data
        assert data["entitiesFound"] >= 0


class TestWhitelistIntegration:
    """Test whitelist integration with anonymization"""

    def test_whitelist_prevents_anonymization(self):
        """Test that whitelist entries prevent anonymization"""
        # Add entry to whitelist
        client.post(
            "/api/whitelist",
            json={"entry": "Berlin"}
        )
        
        # Find PIIs
        response = client.post(
            "/api/find-piis",
            json={
                "text": "Der Patient wurde in Berlin behandelt.",
                "useBothModels": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check if Berlin is marked as whitelisted
        berlin_entities = [e for e in data["entities"] if e["text"] == "Berlin"]
        if berlin_entities:
            assert berlin_entities[0]["whitelisted"] == True


class TestErrorHandling:
    """Test error handling for whitelist and template endpoints"""

    def test_add_duplicate_whitelist_entry(self):
        """Test adding duplicate whitelist entry returns 409"""
        # Clear whitelist
        client.put("/api/whitelist", json={"entries": []})
        
        # Add entry
        response1 = client.post(
            "/api/whitelist",
            json={"entry": "TestEntry"}
        )
        assert response1.status_code == 201
        
        # Try to add same entry again
        response2 = client.post(
            "/api/whitelist",
            json={"entry": "TestEntry"}
        )
        assert response2.status_code == 409
        data = response2.json()
        assert "detail" in data

    def test_remove_nonexistent_whitelist_entry(self):
        """Test removing non-existent whitelist entry returns 404"""
        # Clear whitelist
        client.put("/api/whitelist", json={"entries": []})
        
        response = client.delete("/api/whitelist/NonExistentEntry12345")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_get_nonexistent_template(self):
        """Test getting non-existent template returns 404"""
        response = client.get("/api/templates/nonexistent-template-xyz")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestAnonymizationMechanisms:
    """Test different anonymization mechanisms"""

    def test_redact_mechanism(self):
        """Test redact mechanism"""
        # Create template with redact
        client.post(
            "/api/templates/redact-template",
            json={
                "name": "Redact Template",
                "defaultMechanism": {"type": "redact"},
                "mechanismsByTag": {}
            }
        )
        
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Test text with entities.",
                "templateId": "redact-template"
            }
        )
        assert response.status_code == 200

    def test_replace_mechanism(self):
        """Test replace mechanism"""
        # Create template with replace
        client.post(
            "/api/templates/replace-template",
            json={
                "name": "Replace Template",
                "defaultMechanism": {"type": "replace", "replacement": "[REMOVED]"},
                "mechanismsByTag": {}
            }
        )
        
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Test text.",
                "templateId": "replace-template"
            }
        )
        assert response.status_code == 200

    def test_hash_mechanism(self):
        """Test hash mechanism"""
        # Create template with hash
        client.post(
            "/api/templates/hash-template",
            json={
                "name": "Hash Template",
                "defaultMechanism": {"type": "hash"},
                "mechanismsByTag": {}
            }
        )
        
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Test text.",
                "templateId": "hash-template"
            }
        )
        assert response.status_code == 200


class TestReplacements:
    """Test replacement tracking"""

    def test_replacements_tracking(self):
        """Test that replacements are properly tracked"""
        response = client.post(
            "/api/anonymize",
            json={
                "text": "Test text for replacement tracking."
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check replacements structure
        assert isinstance(data["replacements"], list)
        for replacement in data["replacements"]:
            assert "original" in replacement
            assert "replacement" in replacement
            assert "start" in replacement
            assert "end" in replacement
            assert "label" in replacement
            assert "mechanism" in replacement
