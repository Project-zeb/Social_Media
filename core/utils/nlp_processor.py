import spacy

# Load the NLP model
nlp = spacy.load("en_core_web_sm")

def extract_location(text):
    """
    ULTRA-NICE EXTRACTION: 
    1. Uses spaCy to find Geopolitical Entities (GPE).
    2. Uses a case-insensitive backup check for your primary North India cities.
    """
    doc = nlp(text)
    
    # 1. Try spaCy's built-in entity recognition
    for ent in doc.ents:
        if ent.label_ == "GPE":
            return ent.text.capitalize()
    
    # 2. PRO BACKUP: Check for your grid-defined cities manually
    # Add any cities from your coordinate_districts_v3.csv here
    common_cities = ['Patna', 'Lucknow', 'Varanasi', 'Dehradun', 'Delhi', 'Kanpur', 'Agra']
    
    text_lower = text.lower()
    for city in common_cities:
        if city.lower() in text_lower:
            return city
            
    return None

def identify_disaster_type(text):
    """
    ULTRA-NICE CLASSIFICATION:
    Uses "Keyword Bundles" to catch contextual clues like 'Ganga' or 'Rising'.
    """
    text = text.lower()

    # FLOOD BUNDLE (Captures synonyms and local terms)
    flood_clues = ['flood', 'pani', 'baadh', 'submerged', 'water level', 'rising', 'ganga', 'yamuna', 'river']
    if any(word in text for word in flood_clues):
        return 'FLOOD'

    # FIRE BUNDLE
    fire_clues = ['fire', 'aag', 'smoke', 'burning', 'blaze', 'forest fire', 'short circuit']
    if any(word in text for word in fire_clues):
        return 'FIRE'

    # STORM BUNDLE
    storm_clues = ['storm', 'rain', 'hawa', 'bijli', 'thunder', 'cyclone', 'winds', 'andhi']
    if any(word in text for word in storm_clues):
        return 'STORM'

    return None