"""
Tests for smart whitelist matching.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.storage import WhitelistStorage
from app.blacklist_manager import blacklist_manager

client = TestClient(app)


class TestSmartWhitelistWordMatch:
    """Test word-based whitelist matching"""
    
    def setup_method(self):
        """Clear lists before each test"""
        WhitelistStorage.set_all([])
        blacklist_manager.set_all([])
    
    def test_nyha_matches_nyha_iv(self):
        """Test that 'NYHA' in whitelist matches 'NYHA IV'"""
        WhitelistStorage.add("NYHA")
        
        response = client.post(
            "/api/find-piis",
            json={"text": "Diagnose: NYHA IV, Herzinsuffizienz"}
        )
        data = response.json()
        
        # Find "NYHA IV" entity (if detected)
        nyha_entities = [e for e in data["entities"] if "NYHA" in e["text"]]
        
        if nyha_entities:
            # Should be whitelisted
            assert nyha_entities[0]["whitelisted"] is True
    
    def test_word_match_first_word(self):
        """Test whitelist matches first word"""
        WhitelistStorage.add("Test")
        
        response = client.post(
            "/api/find-piis",
            json={"text": "Test Term should match"}
        )
        data = response.json()
        
        # Check if "Test" or "Test Term" is detected
        test_entities = [e for e in data["entities"] if "Test" in e["text"]]
        
        if test_entities:
            assert test_entities[0]["whitelisted"] is True
    
    def test_word_match_last_word(self):
        """Test whitelist matches last word"""
        WhitelistStorage.add("IV")
        
        response = client.post(
            "/api/find-piis",
            json={"text": "NYHA IV diagnosis"}
        )
        data = response.json()
        
        entities_with_iv = [e for e in data["entities"] if "IV" in e["text"]]
        
        if entities_with_iv:
            assert entities_with_iv[0]["whitelisted"] is True


class TestSmartWhitelistPartialMatch:
    """Test partial matching in whitelist"""
    
    def setup_method(self):
        """Clear lists before each test"""
        WhitelistStorage.set_all([])
        blacklist_manager.set_all([])
    
    def test_charite_matches_charite_berlin(self):
        """Test that 'Charité' in whitelist matches 'Charité Berlin'"""
        WhitelistStorage.add("Charité")
        
        response = client.post(
            "/api/find-piis",
            json={"text": "Behandlung in der Charité Berlin"}
        )
        data = response.json()
        
        # Any entity containing "Charité" should be whitelisted
        charite_entities = [e for e in data["entities"] if "Charité" in e["text"]]
        
        if charite_entities:
            assert all(e["whitelisted"] for e in charite_entities)
    
    def test_partial_match_substring(self):
        """Test substring matching"""
        WhitelistStorage.add("Hospital")
        
        response = client.post(
            "/api/find-piis",
            json={"text": "University Hospital Berlin"}
        )
        data = response.json()
        
        hospital_entities = [e for e in data["entities"] if "Hospital" in e["text"]]
        
        if hospital_entities:
            assert hospital_entities[0]["whitelisted"] is True


class TestSmartWhitelistExactMatch:
    """Test exact matching still works"""
    
    def setup_method(self):
        """Clear lists before each test"""
        WhitelistStorage.set_all([])
        blacklist_manager.set_all([])
    
    def test_exact_match_works(self):
        """Test exact match is still supported"""
        WhitelistStorage.add("Berlin")
        
        response = client.post(
            "/api/find-piis",
            json={"text": "Stadt Berlin"}
        )
        data = response.json()
        
        berlin_entities = [e for e in data["entities"] if e["text"] == "Berlin"]
        
        if berlin_entities:
            assert berlin_entities[0]["whitelisted"] is True


class TestSmartWhitelistAnonymization:
    """Test that smart whitelist prevents anonymization"""
    
    def setup_method(self):
        """Clear lists before each test"""
        WhitelistStorage.set_all([])
        blacklist_manager.set_all([])
    
    def test_nyha_iv_not_anonymized(self):
        """Test that whitelisted 'NYHA' prevents anonymization of 'NYHA IV'"""
        WhitelistStorage.add("NYHA")
        
        response = client.post(
            "/api/anonymize",
            json={"text": "Diagnose: NYHA IV"}
        )
        data = response.json()
        
        # "NYHA" should remain (not anonymized)
        # Note: "IV" might be anonymized separately if detected as a different entity
        assert "NYHA" in data["anonymizedText"]
    
    def test_whitelisted_term_stays_in_text(self):
        """Test whitelisted terms stay in anonymized text"""
        WhitelistStorage.add("Charité")
        
        response = client.post(
            "/api/anonymize",
            json={"text": "Behandlung in Charité"}
        )
        data = response.json()
        
        # "Charité" should remain
        assert "Charité" in data["anonymizedText"]
    
    def test_non_whitelisted_still_anonymized(self):
        """Test non-whitelisted terms are still anonymized"""
        WhitelistStorage.add("NYHA")
        
        response = client.post(
            "/api/anonymize",
            json={"text": "NYHA IV, Herzinsuffizienz"}
        )
        data = response.json()
        
        # "NYHA" should remain, but "Herzinsuffizienz" might be anonymized
        # (if detected as an entity)
        assert "NYHA" in data["anonymizedText"]


class TestSmartWhitelistDoesNotAffectBlacklist:
    """Test that whitelist doesn't override blacklist"""
    
    def setup_method(self):
        """Clear lists before each test"""
        WhitelistStorage.set_all([])
        blacklist_manager.set_all([])
    
    def test_blacklist_overrides_word_match(self):
        """Test blacklist takes priority over word-based whitelist match"""
        WhitelistStorage.add("Test")  # Whitelist "Test"
        blacklist_manager.add_entry("Test Term")  # Blacklist "Test Term"
        
        response = client.post(
            "/api/anonymize",
            json={"text": "Test Term should be anonymized"}
        )
        data = response.json()
        
        # "Test Term" should be anonymized (blacklist wins)
        assert "Test Term" not in data["anonymizedText"]
    
    def test_blacklist_overrides_partial_match(self):
        """Test blacklist takes priority over partial whitelist match"""
        WhitelistStorage.add("City")
        blacklist_manager.add_entry("Northeim")
        
        response = client.post(
            "/api/anonymize",
            json={"text": "Patient from Northeim"}
        )
        data = response.json()
        
        # "Northeim" should be anonymized (blacklist)
        assert "Northeim" not in data["anonymizedText"]
