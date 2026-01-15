"""
Tests for multi-title detection fix.
"""
import pytest
from app.pii_patterns import regex_detector


class TestMultiTitleDetection:
    """Test that multi-title patterns work correctly"""
    
    def test_prof_dr_with_name(self):
        """Test that 'Prof. Dr. Wagner' is fully detected"""
        text = "Konsultation bei Prof. Dr. Wagner"
        entities = regex_detector.find_titles(text)
        
        # Should find the full match (may have overlaps before deduplication)
        full_matches = [e for e in entities if e["text"] == "Prof. Dr. Wagner"]
        assert len(full_matches) >= 1, f"Full match not found in: {entities}"
        assert full_matches[0]["label"] == "PERSON"
        assert full_matches[0]["source"] == "regex_title"
    
    def test_prof_dr_med_with_name(self):
        """Test 'Prof. Dr. med. Schmidt'"""
        text = "Behandelt von Prof. Dr. med. Schmidt"
        entities = regex_detector.find_titles(text)
        
        # Should find the full match with all parts
        full_matches = [e for e in entities if "Schmidt" in e["text"] and "Prof. Dr. med." in e["text"]]
        assert len(full_matches) >= 1, f"Full match not found in: {entities}"
    
    def test_dr_prof_with_name(self):
        """Test 'Dr. Prof. Müller' (reverse order)"""
        text = "Notfall: Dr. Prof. Müller"
        entities = regex_detector.find_titles(text)
        
        # Should find the full match
        full_matches = [e for e in entities if "Müller" in e["text"] and "Dr. Prof." in e["text"]]
        assert len(full_matches) >= 1, f"Full match not found in: {entities}"
    
    def test_double_name(self):
        """Test 'Dr. Lisa Müller' (double name)"""
        text = "Notfall: Dr. Lisa Müller"
        entities = regex_detector.find_titles(text)
        
        assert len(entities) == 1
        assert entities[0]["text"] == "Dr. Lisa Müller"
    
    def test_prof_dr_med_double_name(self):
        """Test 'Prof. Dr. med. Anna Schmidt'"""
        text = "Überwiesen von Prof. Dr. med. Anna Schmidt"
        entities = regex_detector.find_titles(text)
        
        # Should find the full match with double name
        full_matches = [e for e in entities if "Anna Schmidt" in e["text"]]
        assert len(full_matches) >= 1, f"Full match not found in: {entities}"


class TestSingleTitleRegression:
    """Test that simple titles still work (regression tests)"""
    
    def test_simple_dr_title(self):
        """Test that simple 'Dr. Schmidt' still works"""
        text = "Überwiesen von Dr. Schmidt"
        entities = regex_detector.find_titles(text)
        
        assert len(entities) == 1
        assert entities[0]["text"] == "Dr. Schmidt"
    
    def test_simple_prof_title(self):
        """Test 'Prof. Wagner'"""
        text = "Konsultation bei Prof. Wagner"
        entities = regex_detector.find_titles(text)
        
        assert len(entities) == 1
        assert entities[0]["text"] == "Prof. Wagner"
    
    def test_dr_med_title(self):
        """Test 'Dr. med. Müller'"""
        text = "Behandelt von Dr. med. Müller"
        entities = regex_detector.find_titles(text)
        
        assert len(entities) == 1
        assert entities[0]["text"] == "Dr. med. Müller"
    
    def test_dipl_med_title(self):
        """Test 'Dipl.-Med. Schmidt'"""
        text = "Konsultation Dipl.-Med. Schmidt"
        entities = regex_detector.find_titles(text)
        
        assert len(entities) == 1
        assert entities[0]["text"] == "Dipl.-Med. Schmidt"


class TestTitleEdgeCases:
    """Test edge cases for title detection"""
    
    def test_multiple_titles_in_text(self):
        """Test multiple different titles in same text"""
        text = "Dr. Schmidt und Prof. Dr. Wagner arbeiten zusammen"
        entities = regex_detector.find_titles(text)
        
        # Should find both
        assert len(entities) >= 2
        names = [e["text"] for e in entities]
        assert any("Schmidt" in name for name in names)
        assert any("Wagner" in name for name in names)
    
    def test_title_at_start(self):
        """Test title at start of text"""
        text = "Prof. Dr. Wagner behandelt Patienten"
        entities = regex_detector.find_titles(text)
        
        # Should find the full match
        full_matches = [e for e in entities if e["text"] == "Prof. Dr. Wagner"]
        assert len(full_matches) >= 1
        assert full_matches[0]["start"] == 0
    
    def test_title_at_end(self):
        """Test title at end of text"""
        text = "Behandelt von Prof. Dr. Wagner"
        entities = regex_detector.find_titles(text)
        
        # Should find the full match
        full_matches = [e for e in entities if e["text"] == "Prof. Dr. Wagner"]
        assert len(full_matches) >= 1
        assert full_matches[0]["end"] == len(text)
    
    def test_german_umlauts_in_name(self):
        """Test German umlauts in names"""
        text = "Dr. Müller und Prof. Schäfer"
        entities = regex_detector.find_titles(text)
        
        assert len(entities) == 2
        names = [e["text"] for e in entities]
        assert any("Müller" in name for name in names)
        assert any("Schäfer" in name for name in names)
