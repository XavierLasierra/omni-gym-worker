import re
import unicodedata

def normalize_class_name(s: str) -> str:
    """Removes accents and non-alphanumeric characters for fuzzy matching."""
    s = s.lower()
    # Normalize to NFD and filter out non-spacing marks (accents)
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    # Unify common variations (like Gym vs Gim)
    s = s.replace('gim', 'gym')
    # Remove everything that is not a-z or 0-9
    return re.sub(r'[^a-z0-9]', '', s)
