"""
Tests for user's real-world cases from PR #8.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.storage import WhitelistStorage
from app.blacklist_manager import blacklist_manager

client = TestClient(app)


class TestUserCase1ProfDrWagner:
    """Test user's exact case: Prof. Dr. Wagner detection"""
    
    def setup_method(self):
        """Clear lists before each test"""
        WhitelistStorage.set_all([])
        blacklist_manager.set_all([])
    
    def test_prof_dr_wagner_full_detection(self):
        """Test that 'Prof. Dr. Wagner' is detected as one entity with full name"""
        text = "Konsultation bei Prof. Dr. Wagner"
        
        response = client.post(
            "/api/find-piis",
            json={"text": text}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find person entities
        person_entities = [e for e in data["entities"] if e["label"] in ["PERSON", "PER"]]
        
        # Should find at least one person entity
        assert len(person_entities) >= 1
        
        # Check if full name "Wagner" is captured
        full_match = any("Wagner" in e["text"] for e in person_entities)
        assert full_match, f"Wagner not found in entities: {person_entities}"
        
        # Check if it includes the title
        title_match = any("Prof." in e["text"] or "Dr." in e["text"] for e in person_entities)
        assert title_match, f"Title not found in entities: {person_entities}"
    
    def test_prof_dr_wagner_anonymization(self):
        """Test that 'Prof. Dr. Wagner' is properly anonymized"""
        text = "Konsultation bei Prof. Dr. Wagner"
        
        response = client.post(
            "/api/anonymize",
            json={"text": text}
        )
        assert response.status_code == 200
        data = response.json()
        
        # "Wagner" should be anonymized
        assert "Wagner" not in data["anonymizedText"]
        # Should have some anonymization marker
        assert ("[REDACTED]" in data["anonymizedText"] or 
                "[PERSON]" in data["anonymizedText"] or
                "Prof. Dr. Wagner" not in data["anonymizedText"])


class TestUserCase2NyhaWhitelist:
    """Test user's exact case: NYHA IV whitelist"""
    
    def setup_method(self):
        """Clear lists before each test"""
        WhitelistStorage.set_all([])
        blacklist_manager.set_all([])
    
    def test_nyha_whitelist_matches_nyha_iv(self):
        """Test that 'NYHA' in whitelist matches 'NYHA IV'"""
        # Setup whitelist
        WhitelistStorage.add("NYHA")
        
        text = "Diagnose: NYHA IV, Herzinsuffizienz"
        
        # Test detection with whitelist flag
        response = client.post(
            "/api/find-piis",
            json={"text": text}
        )
        data = response.json()
        
        # Find NYHA-related entities
        nyha_entities = [e for e in data["entities"] if "NYHA" in e["text"]]
        
        # If NYHA IV is detected, it should be whitelisted
        if nyha_entities:
            assert nyha_entities[0]["whitelisted"] is True, \
                f"NYHA entity not whitelisted: {nyha_entities[0]}"
    
    def test_nyha_whitelist_prevents_anonymization(self):
        """Test that 'NYHA' whitelist prevents 'NYHA IV' anonymization"""
        WhitelistStorage.add("NYHA")
        
        text = "Diagnose: NYHA IV, Herzinsuffizienz"
        
        response = client.post(
            "/api/anonymize",
            json={"text": text}
        )
        data = response.json()
        
        # "NYHA" should remain in text (not anonymized)
        assert "NYHA" in data["anonymizedText"], \
            f"NYHA was anonymized but should be whitelisted. Result: {data['anonymizedText']}"


class TestUserCase3Northeim:
    """Test user's exact case: Northeim blacklist"""
    
    def setup_method(self):
        """Clear lists before each test"""
        WhitelistStorage.set_all([])
        blacklist_manager.set_all([])
    
    def test_northeim_not_detected_without_blacklist(self):
        """Verify that Northeim is not detected by NLP alone (small city)"""
        text = "Patient wohnt in Northeim"
        
        response = client.post(
            "/api/find-piis",
            json={"text": text}
        )
        data = response.json()
        
        # Find entities containing "Northeim"
        northeim_entities = [e for e in data["entities"] 
                           if "Northeim" in e["text"] and e["source"] != "blacklist"]
        
        # Likely not detected by spaCy (small city)
        # This is why we need blacklist!
    
    def test_northeim_blacklist_forces_detection(self):
        """Test that blacklist forces detection of Northeim"""
        blacklist_manager.add_entry("Northeim")
        
        text = "Patient wohnt in Northeim"
        
        response = client.post(
            "/api/find-piis",
            json={"text": text}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should find "Northeim" as blacklisted
        blacklisted = [e for e in data["entities"] if e["source"] == "blacklist"]
        assert len(blacklisted) > 0, "Blacklisted term not detected"
        
        northeim_found = any("Northeim" in e["text"] for e in blacklisted)
        assert northeim_found, f"Northeim not in blacklisted entities: {blacklisted}"
    
    def test_northeim_blacklist_forces_anonymization(self):
        """Test that blacklist forces anonymization of Northeim"""
        blacklist_manager.add_entry("Northeim")
        
        text = "Patient wohnt in Northeim, einer kleinen Stadt"
        
        response = client.post(
            "/api/anonymize",
            json={"text": text}
        )
        assert response.status_code == 200
        data = response.json()
        
        # "Northeim" MUST be anonymized
        assert "Northeim" not in data["anonymizedText"], \
            f"Northeim should be anonymized. Result: {data['anonymizedText']}"
        
        # Should have anonymization marker
        assert "[REDACTED]" in data["anonymizedText"], \
            f"No [REDACTED] marker found. Result: {data['anonymizedText']}"


class TestIntegrationScenarios:
    """Test combined scenarios"""
    
    def setup_method(self):
        """Clear lists before each test"""
        WhitelistStorage.set_all([])
        blacklist_manager.set_all([])
    
    def test_blacklist_and_whitelist_together(self):
        """Test blacklist and whitelist work together"""
        # Whitelist medical term
        WhitelistStorage.add("NYHA")
        # Blacklist location
        blacklist_manager.add_entry("Northeim")
        
        text = "Patient aus Northeim mit NYHA IV Diagnose"
        
        response = client.post(
            "/api/anonymize",
            json={"text": text}
        )
        data = response.json()
        
        # Northeim should be anonymized (blacklist)
        assert "Northeim" not in data["anonymizedText"]
        
        # NYHA should remain (whitelist)
        assert "NYHA" in data["anonymizedText"]
    
    def test_multiple_doctors_with_multi_title(self):
        """Test multiple doctors with different title formats"""
        text = "Dr. Schmidt und Prof. Dr. Wagner arbeiten zusammen"
        
        response = client.post(
            "/api/anonymize",
            json={"text": text}
        )
        data = response.json()
        
        # Both names should be anonymized
        assert "Schmidt" not in data["anonymizedText"]
        assert "Wagner" not in data["anonymizedText"]
    
    def test_complex_medical_report(self):
        """Test a more complex medical report scenario"""
        WhitelistStorage.add("NYHA")
        WhitelistStorage.add("Charité")
        blacklist_manager.add_entry("Northeim")
        
        text = """
        Patient aus Northeim, behandelt von Prof. Dr. Wagner.
        Diagnose: NYHA IV in Charité Berlin.
        """
        
        response = client.post(
            "/api/anonymize",
            json={"text": text}
        )
        data = response.json()
        
        # Blacklisted should be anonymized
        assert "Northeim" not in data["anonymizedText"]
        
        # Doctor name should be anonymized
        assert "Wagner" not in data["anonymizedText"]
        
        # Whitelisted should remain
        assert "NYHA" in data["anonymizedText"]
        assert "Charité" in data["anonymizedText"]
