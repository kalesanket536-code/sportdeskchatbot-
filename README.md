# SportDesk – Lightweight Sports Event Assistant

A lightweight, zero-GPU conversational AI assistant designed for sports tournament operations, athletes, and spectators. 

Instead of brittle `if/else` keyword trees, **SportDesk** pairs an **NLTK NLP preprocessing pipeline** and **TF-IDF Cosine Similarity** with a **dynamic SQLite live-event database** to deliver real-time tournament schedules, weather holds, venue directions, and regulations with sub-25ms CPU latency.

---

## Key Features

- **No Rigid `if/else` Rules**: Uses NLTK tokenization, WordNet lemmatization, domain synonym expansion, and TF-IDF vector similarity.
- **Dynamic Live-Event State**: Connects to an internal SQLite database for live fixture schedules, delay announcements, and facility lookups rather than serving stale hardcoded strings.
- **Clean Apple System Light UI**: Built using the Apple Human Interface design tokens:
  - Primary Action: `#0066CC` (Apple Blue)
  - Surface Background: `#FFFFFF` (White)
  - Secondary Background: `#F5F5F7` (Light Gray)
  - Selection Highlight: `#E8F2FF` (Light Blue)
  - Status Indicator: `#34C759` (Apple Green)
  - Text & Borders: `#1D1D1F` (Primary), `#6E6E73` (Secondary), `#D2D2D7` (Border)
- **Zero GPU Requirement**: Runs entirely on low-tier CPU instances (<120MB RAM footprint).
- **Dual Interfaces**: Web UI (FastAPI + Tailwind) and Terminal CLI.

---

## Project Structure

```
cool-fermi/
├── app.py                     # FastAPI application & REST API
├── cli.py                     # Interactive terminal CLI
├── requirements.txt           # Minimal dependencies
├── README.md                  # Documentation
├── engine/
│   ├── __init__.py
│   ├── nlp.py                 # NLTK tokenization, lemmatization, TF-IDF cosine similarity
│   └── event_db.py            # SQLite live fixtures, delays & facilities database
├── data/
│   ├── sports_intents.json    # Sports event taxonomy & knowledge base
│   └── sports_event.db        # Auto-seeded SQLite database
└── static/
    └── index.html             # Apple System Light web UI
```

---

## Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

*(NLTK tokenizers and WordNet data are automatically downloaded on first startup).*

### 2. Launch the Web Interface
```bash
python3 app.py
```
Open your browser to:
👉 **http://127.0.0.1:8000**

### 3. Or Run Directly in the Terminal
```bash
python3 cli.py
```

---

## REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/chat` | Send a user message and receive an NLP-matched response |
| `GET` | `/api/fixtures` | Retrieve current tournament fixtures and live match status |
| `GET` | `/api/delays` | Check active weather, rain holds, or court delays |
| `POST` | `/api/delays` | Event organizers can report an active delay in real time |
| `GET` | `/api/facilities` | Lookup medical tents, hydration zones, and box offices |
| `GET` | `/api/status` | Health check and cached corpus statistics |

### Sample Chat Request
```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "When is the 100m sprint final?"}'
```

Response:
```json
{
  "matched": true,
  "confidence": 1.0,
  "intent": "fixture_schedule",
  "response": "Here is the current live schedule:\n• 100m Sprint Final (Track & Field): 04:15 PM at Main Track A [Upcoming]\n• 400m Hurdles (Track & Field): 02:30 PM at Main Track A [Live]",
  "source": "Live Fixtures DB"
}
```

---

## License
MIT
