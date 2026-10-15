import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

from engine.event_db import get_fixtures, get_active_delays, get_facilities

def get_live_context_prompt() -> str:
    """Builds a live event ground-truth snapshot for Gemini."""
    fixtures = get_fixtures()
    delays = get_active_delays()
    facilities = get_facilities()

    context_lines = [
        "### CURRENT LIVE TOURNAMENT CONTEXT (GROUND TRUTH):",
        "--- LIVE FIXTURES & TIMETABLE ---"
    ]
    for f in fixtures:
        context_lines.append(f"• {f['event_name']} ({f['sport']}): {f['start_time']} at {f['court']} - Status: {f['status']}. Notes: {f['notes']}")

    context_lines.append("\n--- ACTIVE DELAYS & WEATHER ALERTS ---")
    if delays:
        for d in delays:
            context_lines.append(f"• {d['location']}: {d['message']} ({d['delay_minutes']} min delay)")
    else:
        context_lines.append("• Zero active weather or schedule delays. All courts and tracks are dry and on time.")

    context_lines.append("\n--- VENUE FACILITIES & SERVICES ---")
    for fac in facilities:
        context_lines.append(f"• {fac['name']}: {fac['location']} (Near {fac['gate_proximity']}) - {fac['details']}")

    context_lines.append("\n--- GENERAL EVENT RULES & LOGISTICS ---")
    context_lines.append("• Spikes: Only 6mm pyramid/ceramic spikes allowed on synthetic tracks. Metal tree spikes strictly prohibited.")
    context_lines.append("• Parking: Lot B & Lot C open ($10 day pass). Free electric shuttles run every 6 mins to the stadium.")
    context_lines.append("• Ticketing: Gates 1, 2, 4. Will Call Box Office at Gate 1 North. Under 5 free with adult.")
    context_lines.append("• Check-in: Athlete bib check-in at Indoor Sports Hall Room 102 (closes 45 min prior to heat).")
    context_lines.append("• Staff / Volunteers: Dispatch on Radio Channel 3 (Marshals Channel 2). HQ in Media Center Room 4.")

    return "\n".join(context_lines)

SYSTEM_INSTRUCTION = """You are 'SportDesk', a friendly, concise, and helpful sports event assistant for attendees, athletes, and volunteers.
You answer questions naturally and professionally using the provided ground-truth event data.
Guidelines:
1. Keep answers concise, clear, and direct (2-3 sentences max unless details are requested).
2. Rely strictly on the live tournament context provided. If information is not in the context, politely suggest checking the main information booth at Gate 1.
3. Be warm and encouraging to athletes and visitors.
4. Format lists with clean bullet points when showing multiple items.
"""

def generate_gemini_reply(user_query: str, api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Generates an answer using Gemini 2.5 Flash if API key is available."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key or key.strip() in ("", "YOUR_GEMINI_API_KEY_HERE"):
        return None

    try:
        from google import genai
        client = genai.Client(api_key=key.strip())
        
        live_context = get_live_context_prompt()
        prompt = f"{live_context}\n\nUSER QUESTION: {user_query}\n\nANSWER:"

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": SYSTEM_INSTRUCTION,
                "temperature": 0.4
            }
        )

        reply_text = response.text.strip() if response.text else "Information is currently unavailable."
        return {
            "matched": True,
            "confidence": 0.99,
            "intent": "gemini_conversational",
            "response": reply_text,
            "source": "Gemini 2.5 Flash + Live Event DB"
        }
    except Exception as e:
        print(f"[Gemini Error]: {e}")
        return None
