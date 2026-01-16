"""
Tests for blacklist functionality.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.blacklist_manager import blacklist_manager

client = TestClient(app)


class TestBlacklistCRUD:
    """Test blacklist CRUD operations"""
    
    def setup_method(self):
        """Clear blacklist before each test"""
        blacklist_manager.set_all([])
    
    def test_add_blacklist_entry(self):
        """Test adding entry to blacklist"""
        response = client.post(
            "/api/blacklist",
            json={"entry": "Northeim"}
        )
        assert response.status_code == 201
        assert response.json()["success"] is True
        
        # Verify it was added
        response = client.get("/api/blacklist")
        assert response.status_code == 200
        assert "Northeim" in response.json()["entries"]
    
    def test_add_duplicate_blacklist_entry(self):
        """Test adding duplicate entry"""
        client.post("/api/blacklist", json={"entry": "Northeim"})
        response = client.post("/api/blacklist", json={"entry": "Northeim"})
        assert response.status_code == 409  # Conflict
    
    def test_get_blacklist(self):
        """Test getting all blacklist entries"""
        blacklist_manager.add_entry("Term1")
        blacklist_manager.add_entry("Term2")
        
        response = client.get("/api/blacklist")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 2
        assert "Term1" in data["entries"]
        assert "Term2" in data["entries"]
    
    def test_delete_blacklist_entry(self):
        """Test deleting entry from blacklist"""
        blacklist_manager.add_entry("Northeim")
        
        response = client.delete("/api/blacklist/Northeim")
        assert response.status_code == 200
        
        # Verify deleted
        response = client.get("/api/blacklist")
        assert "Northeim" not in response.json()["entries"]
    
    def test_delete_nonexistent_entry(self):
        """Test deleting entry that doesn't exist"""
        response = client.delete("/api/blacklist/NonExistent")
        assert response.status_code == 404
    
    def test_replace_blacklist(self):
        """Test replacing entire blacklist"""
        blacklist_manager.add_entry("OldTerm")
        
        response = client.put(
            "/api/blacklist",
            json={"entries": ["NewTerm1", "NewTerm2"]}
        )
        assert response.status_code == 200
        
        # Verify replacement
        response = client.get("/api/blacklist")
        data = response.json()
        assert "OldTerm" not in data["entries"]
        assert "NewTerm1" in data["entries"]
        assert "NewTerm2" in data["entries"]


class TestBlacklistFunctionality:
    """Test blacklist forces anonymization"""
    
    def setup_method(self):
        """Clear blacklist before each test"""
        blacklist_manager.set_all([])
    
    def test_blacklist_forces_detection(self):
        """Test that blacklisted terms are detected"""
        blacklist_manager.add_entry("Northeim")
        
        response = client.post(
            "/api/find-piis",
            json={"text": "Patient wohnt in Northeim, einer kleinen Stadt"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Find "Northeim" in entities
        northeim_entities = [e for e in data["entities"] if "Northeim" in e["text"]]
        assert len(northeim_entities) > 0
        assert northeim_entities[0]["label"] == "BLACKLISTED"
        assert northeim_entities[0]["source"] == "blacklist"
    
    def test_blacklist_forces_anonymization(self):
        """Test that blacklisted terms are always anonymized"""
        blacklist_manager.add_entry("Northeim")
        
        response = client.post(
            "/api/anonymize",
            json={"text": "Patient wohnt in Northeim"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # "Northeim" should be anonymized
        assert "Northeim" not in data["anonymizedText"]
        assert "[REDACTED]" in data["anonymizedText"]
    
    def test_blacklist_case_insensitive(self):
        """Test blacklist is case-insensitive"""
        blacklist_manager.add_entry("Northeim")
        
        response = client.post(
            "/api/find-piis",
            json={"text": "Patient aus northeim und NORTHEIM"}
        )
        data = response.json()
        
        # Should find both lowercase and uppercase
        northeim_entities = [e for e in data["entities"] if e["label"] == "BLACKLISTED"]
        assert len(northeim_entities) == 2
    
    def test_blacklist_overrides_whitelist(self):
        """Test that blacklist takes priority over whitelist"""
        # Add to both lists
        client.post("/api/whitelist", json={"entry": "TestTerm"})
        blacklist_manager.add_entry("TestTerm")
        
        # Test anonymization
        response = client.post(
            "/api/anonymize",
            json={"text": "TestTerm should be anonymized"}
        )
        data = response.json()
        
        # Should be anonymized (blacklist wins)
        assert "TestTerm" not in data["anonymizedText"]
        assert "[REDACTED]" in data["anonymizedText"]
    
    def test_blacklisted_not_whitelisted(self):
        """Test blacklisted items are never marked as whitelisted"""
        client.post("/api/whitelist", json={"entry": "TestTerm"})
        blacklist_manager.add_entry("TestTerm")
        
        response = client.post(
            "/api/find-piis",
            json={"text": "TestTerm is here"}
        )
        data = response.json()
        
        # Find blacklisted entity
        blacklisted = [e for e in data["entities"] if e["source"] == "blacklist"]
        assert len(blacklisted) > 0
        assert blacklisted[0]["whitelisted"] is False
