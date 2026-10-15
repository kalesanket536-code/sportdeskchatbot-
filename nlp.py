import json
import os
import re
from typing import Dict, Any, Tuple, Optional
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from engine.event_db import (
    format_live_fixtures,
    format_live_delays,
    format_live_facilities
)

# Ensure NLTK resources (compatible with serverless / read-only filesystem environments like Vercel)
_nltk_data_dir = os.environ.get("NLTK_DATA", "/tmp/nltk_data")
if _nltk_data_dir not in nltk.data.path:
    nltk.data.path.append(_nltk_data_dir)

try:
    _lemmatizer = WordNetLemmatizer()
    _stopwords = set(stopwords.words('english'))
except LookupError:
    os.makedirs(_nltk_data_dir, exist_ok=True)
    for pkg in ('punkt', 'punkt_tab', 'stopwords', 'wordnet'):
        try:
            nltk.download(pkg, download_dir=_nltk_data_dir, quiet=True)
        except Exception:
            pass
    _lemmatizer = WordNetLemmatizer()
    _stopwords = set(stopwords.words('english'))

# Domain Synonyms to prevent keyword-mismatch flaws
SPORTS_SYNONYMS = {
    "semis": "semi-final",
    "semi": "semi-final",
    "finals": "final",
    "ko": "knockout",
    "ref": "referee",
    "ump": "umpire",
    "pitch": "court",
    "field": "court",
    "turf": "track",
    "cleats": "spikes",
    "shoes": "spikes",
    "footwear": "spikes",
    "doctor": "medical",
    "paramedic": "medical",
    "ambulance": "medical",
    "bandage": "medical",
    "first-aid": "medical",
    "drink": "hydration",
    "beverage": "hydration",
    "drinks": "hydration",
    "rain": "weather",
    "storm": "weather",
    "wet": "weather",
    "postponed": "delay",
    "hold": "delay",
    "parking": "park",
    "automobile": "car",
    "tickets": "ticket",
    "passes": "ticket",
    "pass": "ticket"
}

class SportsNLPEngine:
    def __init__(self, intents_path: Optional[str] = None):
        if not intents_path:
            intents_path = os.path.join(os.path.dirname(__file__), "..", "data", "sports_intents.json")
        self.intents_path = intents_path
        self.vectorizer = TfidfVectorizer(
            tokenizer=self.preprocess_text,
            ngram_range=(1, 2),
            sublinear_tf=True
        )
        self.corpus_patterns = []
        self.corpus_intents = []
        self.intent_data_map = {}
        self.tfidf_matrix = None
        self.load_intents()

    def preprocess_text(self, text: str) -> list[str]:
        """Tokenize, expand domain synonyms, lemmatize, and filter noise words."""
        text = text.lower()
        # Clean non-alphanumeric except hyphens
        text = re.sub(r'[^a-zA-Z0-9\-\s]', ' ', text)
        tokens = word_tokenize(text)
        
        cleaned_tokens = []
        for token in tokens:
            if token in _stopwords and token not in {"where", "when", "who", "what"}:
                continue
            # Apply domain synonyms
            norm_token = SPORTS_SYNONYMS.get(token, token)
            # Lemmatize
            lemma = _lemmatizer.lemmatize(norm_token)
            cleaned_tokens.append(lemma)
            
        return cleaned_tokens

    def load_intents(self):
        with open(self.intents_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.corpus_patterns = []
        self.corpus_intents = []
        self.intent_data_map = {}

        for intent in data.get("intents", []):
            tag = intent["tag"]
            self.intent_data_map[tag] = intent
            for pattern in intent.get("patterns", []):
                self.corpus_patterns.append(pattern)
                self.corpus_intents.append(tag)

        # Fit TF-IDF matrix over all reference patterns
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus_patterns)

    def extract_entity_hints(self, query: str) -> Dict[str, Any]:
        """Extract lightweight sport or court anchors from query."""
        q = query.lower()
        hints = {"sport": None, "court": None}
        if "100m" in q or "sprint" in q or "track" in q or "hurdles" in q:
            hints["sport"] = "Track & Field"
        elif "basketball" in q or "hoop" in q:
            hints["sport"] = "Basketball"
        elif "volleyball" in q:
            hints["sport"] = "Volleyball"
        elif "swimming" in q or "pool" in q:
            hints["sport"] = "Swimming"

        court_match = re.search(r'court\s*([0-9a-zA-Z]+)|track\s*([0-9a-zA-Z]+)', q)
        if court_match:
            hints["court"] = court_match.group(0).capitalize()
        return hints

    def predict(self, query: str, threshold: float = 0.32) -> Dict[str, Any]:
        """Predict user intent and generate real-time contextual response."""
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        best_index = similarities.argmax()
        highest_score = float(similarities[best_index])

        if highest_score < threshold:
            return {
                "matched": False,
                "confidence": round(highest_score, 2),
                "intent": "unknown",
                "response": "I couldn't locate an exact match in the event timetable. Try asking about 100m finals, medical tents, delays, parking, or spike rules.",
                "source": "fallback"
            }

        matched_tag = self.corpus_intents[best_index]
        intent_info = self.intent_data_map.get(matched_tag, {})
        dynamic_type = intent_info.get("dynamic_query")
        entity_hints = self.extract_entity_hints(query)

        # Dynamic routing to Live Database instead of stale strings
        if dynamic_type == "fixtures":
            response = format_live_fixtures(entity_hints.get("sport"))
            source = "Live Fixtures DB"
        elif dynamic_type == "delays":
            response = format_live_delays()
            source = "Real-time Weather & Alerts"
        elif dynamic_type == "facilities":
            response = format_live_facilities(entity_hints.get("court") or "")
            source = "Venue Facilities DB"
        else:
            # Fall back to curated response template
            responses = intent_info.get("responses", ["Information available at the central desk."])
            response = responses[0]
            source = "Official Event Guidelines"

        return {
            "matched": True,
            "confidence": round(highest_score, 2),
            "intent": matched_tag,
            "response": response,
            "source": source
        }

# Global singleton engine instance
engine = SportsNLPEngine()
