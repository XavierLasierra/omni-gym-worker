import pytest

from app.utils.strings import normalize_class_name

def test_normalize_class_name():
    # Test basic lowercasing and alphanumeric extraction
    assert normalize_class_name("Yoga 101") == "yoga101"
    
    # Test accent removal
    assert normalize_class_name("Gimnasio Español") == "gymnasioespanol"
    assert normalize_class_name("Áéíóú") == "aeiou"
    
    # Test "gim" to "gym" conversion
    assert normalize_class_name("Gimnasia") == "gymnasia"
    assert normalize_class_name("Body Gim") == "bodygym"
    
    # Test complex characters and symbols
    assert normalize_class_name("  Cross-fit! (Advanced)  ") == "crossfitadvanced"
    
    # Test empty string
    assert normalize_class_name("") == ""
