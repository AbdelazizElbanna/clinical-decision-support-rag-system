"""
Groq-based extraction of structured medical context from user query.
Now also handles updating the working memory (chat_summary) based on each new query.
"""

import json
import re
from groq import Groq
from config import GROQ_API_KEYS, LLM_MODEL
from groq_router import groq_router

# client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are a medical context extractor for a dermatology RAG system.

Given:
1. A new user query
2. An optional previous chat summary (previous context of the conversation)
3. Optional patient profile data (age, gender, notes)

Your job is to:
A) Extract structured intent from the NEW query.
B) Update the `clinical_summary` field to reflect ALL known information from BOTH the previous summary AND the new query (merge, don't discard old info unless overridden).

Rules:
- Normalize drug names to INN (e.g. 'Zyrtec' -> 'cetirizine')
- Map location to the exact city name mentioned. If multiple cities are mentioned (e.g., traveling from A to B), ALWAYS extract the DESTINATION (B) as the location. Set to 'None' if no location is mentioned.
- Set 'requires_weather' to 'true' if ANY city or location is mentioned, or if the user asks about environmental triggers.
- The 'clinical_summary' should be a concise string (max 50 words) summarizing: condition, location, symptoms, relevant medications mentioned so far.
- ALWAYS include BOTH 'diseases' and 'drugs' in collections_to_query if the user asks about treatments, moisturizers, creams, or how to manage a condition.
- You MUST respond ONLY with a raw JSON object (no markdown, no backticks).

CONDITION RE-EVALUATION RULE (CRITICAL):
- If a KNOWN CONDITION is provided from previous context, use it as a prior — but OVERRIDE it if the new query contains symptoms that clearly contradict it.
- Always let the CURRENT SYMPTOMS take priority over the stored condition.
- Example: if stored condition is "Eczema" but user now describes "well-defined silvery plaques on knees/elbows", the correct answer is "Psoriasis", not "Eczema".

CLINICAL DIFFERENTIATORS to help you choose the correct condition:
- Psoriasis: well-defined, thickened plaques with SILVERY or white scales; typically on knees, elbows, scalp, lower back; non-weeping; chronic.
- Eczema (Atopic Dermatitis): poorly-defined, red, weeping or lichenified lesions; typically in flexural areas (inner elbow, behind knees, neck); intense itch; often with personal/family history of atopy.
- Urticaria: raised wheals/hives, transient (hours), severe itch, angioedema possible; no scales.
- General: when the query is about general skin care, drug safety, or the condition cannot be clearly mapped to the above.

JSON Schema:
{
  "is_medical_query": "true | false (false ONLY for absolute greetings/chit-chat like 'hi', 'thanks'. ANY question about care, moisturizers, treatments, or symptoms is TRUE, especially if continuing a previous medical topic)",
  "search_query_en": "short English phrase for vector DB search (CRITICAL: DO NOT DELETE ANY SYMPTOMS. TRANSLATE AND KEEP EVERY DETAIL MENTIONED)",
  "condition": "Eczema | Psoriasis | Urticaria | General | Unknown",
  "governorate": "City name in English, or None",
  "medications_current": ["list"],
  "medications_new": ["list"],
  "collections_to_query": ["diseases", "drugs"],
  "intent": ["ENVIRONMENTAL_WEATHER", "DRUG_SAFETY_CHECK", "DRUG_INTERACTION_CHECK", "SYMPTOM_INQUIRY", "GENERAL_CONDITION_INFO", "GREETING"],
  "requires_weather": "true | false",
  "clinical_summary": "Concise merged summary of ALL known context so far"
}

Examples of GOOD search_query_en:
User: عندي بقع حمرا فيها قشور بتظهر في كوعي ومسببة حكة شديدة بقالها اسبوع
search_query_en: "red plaques with scales on the elbow causing severe itching for one week" (Kept 'red plaques', 'scales', 'elbow', 'severe itching', 'one week')

User: بنتي عندها حساسية في وشها وبتاخد زيرتيك بس مفيش تحسن
search_query_en: "facial allergy taking cetirizine with no improvement" (Kept 'facial', 'allergy', 'cetirizine', 'no improvement')

CRITICAL RULE: Never summarize 'search_query_en' to just the disease name. Translate the full symptom profile into English."""

def extract_intent(query: str, chat_summary: dict = None, patient_profile: dict = None, is_voice: bool = False) -> dict:
    """Extract structured intent and update working memory."""

    # Build context for the extractor
    context_parts = []
    if patient_profile:
        age = patient_profile.get("age")
        gender = patient_profile.get("gender")
        notes = patient_profile.get("notes")
        if age or gender or notes:
            context_parts.append(f"PATIENT PROFILE: Age={age or 'unknown'}, Gender={gender or 'unknown'}, Base Notes={notes or 'none'}")

    if chat_summary and chat_summary.get("clinical_summary"):
        context_parts.append(f"PREVIOUS CHAT SUMMARY: {chat_summary['clinical_summary']}")
    if chat_summary and chat_summary.get("condition") and chat_summary["condition"] not in ("", "Unknown", None):
        context_parts.append(f"KNOWN CONDITION SO FAR: {chat_summary['condition']}")
    if chat_summary and chat_summary.get("governorate") and chat_summary["governorate"] not in ("None", "", None):
        context_parts.append(f"KNOWN LOCATION SO FAR: {chat_summary['governorate']}")

    context_block = "\n".join(context_parts)

    # STT hint: prepend when query came from voice transcription
    stt_hint = ""
    if is_voice:
        stt_hint = (
            "[STT INPUT] This query was transcribed from voice by a speech-to-text model. "
            "Some words may be misrecognized — especially medical terms, drug names, or Arabic dialect words. "
            "Use surrounding context and medical knowledge to infer the most plausible meaning. "
            "Do NOT penalize misspellings of medical terms; treat them as phonetic approximations.\n\n"
        )

    user_message = f"{context_block}\n\n{stt_hint}NEW QUERY: {query}" if context_block else f"{stt_hint}NEW QUERY: {query}"

    try:
        response = groq_router.chat_completion(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1
        )

        content = response.choices[0].message.content or ""
        cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        json_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if json_match:
            args = json.loads(json_match.group(0))
            # Set defaults
            args.setdefault("is_medical_query", True)
            if isinstance(args["is_medical_query"], str):
                args["is_medical_query"] = args["is_medical_query"].lower() == "true"
            args.setdefault("search_query_en", query)
            args.setdefault("medications_current", [])
            args.setdefault("medications_new", [])
            args.setdefault("collections_to_query", ["diseases", "drugs"])
            args.setdefault("condition", "General")
            args.setdefault("governorate", "None")
            args.setdefault("intent", ["GENERAL_CONDITION_INFO"])
            args.setdefault("clinical_summary", query[:100])
            # Normalize requires_weather
            rw = args.get("requires_weather", False)
            args["requires_weather"] = "true" if rw is True or str(rw).lower() == "true" else "false"
            return args

    except Exception as e:
        print("Groq extraction error:", e)

    # Fallback
    prev_summary = (chat_summary or {}).get("clinical_summary", query[:80])
    return {
        "is_medical_query": True,
        "search_query_en": query,
        "condition": (chat_summary or {}).get("condition", "General"),
        "governorate": (chat_summary or {}).get("governorate", "None"),
        "medications_current": [],
        "medications_new": [],
        "collections_to_query": ["diseases", "drugs"],
        "intent": ["GENERAL_CONDITION_INFO"],
        "requires_weather": "false",
        "clinical_summary": prev_summary
    }


