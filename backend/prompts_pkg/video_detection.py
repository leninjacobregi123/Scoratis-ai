import re

VIDEO_WORTHY_KEYWORDS = {
    'high_confidence': [
        'atom', 'electron', 'proton', 'neutron', 'nucleus', 'orbital',
        'gravity', 'force', 'motion', 'velocity', 'acceleration', 'momentum',
        'orbit', 'planet', 'solar system', 'galaxy', 'black hole', 'star',
        'wave', 'frequency', 'amplitude', 'electromagnetic', 'light', 'wavelength',
        'thermodynamics', 'heat', 'energy transfer', 'entropy',
        'quantum', 'relativity', 'spacetime',
        'cell', 'membrane', 'mitochondria', 'organelle',
        'dna', 'rna', 'gene', 'chromosome', 'replication',
        'photosynthesis', 'chlorophyll', 'chloroplast',
        'mitosis', 'meiosis', 'circuit', 'electric', 'voltage'
    ],
    'medium_confidence': [
        'how does', 'how do', 'explain how', 'show me how',
        'visualize', 'demonstrate', 'illustrate',
        'process of', 'mechanism', 'structure of'
    ],
    'exclusions': [
        'code', 'coding', 'programming', 'essay', 'write', 'writing'
    ]
}

def _word_match(keyword: str, text: str) -> bool:
    message_lower = message.lower()

    for keyword in VIDEO_WORTHY_KEYWORDS['exclusions']:
        if _word_match(keyword, message_lower):
            return {'should_offer_video': False, 'confidence': 0.0}

    high_matches = [k for k in VIDEO_WORTHY_KEYWORDS['high_confidence'] if _word_match(k, message_lower)]
    medium_matches = [k for k in VIDEO_WORTHY_KEYWORDS['medium_confidence'] if _word_match(k, message_lower)]

    confidence = 0.0
    if high_matches:
        confidence = min(0.6 + (len(high_matches) * 0.15), 1.0)
    elif len(medium_matches) >= 2:
        confidence = min(0.3 + (len(medium_matches) * 0.1), 0.6)

    return {
        'should_offer_video': confidence >= 0.5,
        'confidence': round(confidence, 2),
        'suggested_topic': high_matches[0].title() if high_matches else None
    }
