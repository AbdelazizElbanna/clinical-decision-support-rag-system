"""
MedLens AI - Stateful RAG Pipeline v2.0
Now accepts patient_profile (from DB) and chat_summary (from LocalStorage working memory).
"""

import asyncio
import re
import json
from groq import Groq
from config import GROQ_API_KEYS, LLM_MODEL
from groq_router import groq_router
from intent_extractor import extract_intent
from retriever import retrieve
from weather_service import resolve_governorate, fetch_weather
from device_utils import get_device

# --- Initialize Reranker ---
try:
    from sentence_transformers import CrossEncoder
    print('Loading Reranker (ms-marco-MiniLM-L-6-v2)...')
    _reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2', max_length=512, device=get_device(), model_kwargs={"use_safetensors": True})
except Exception as e:
    print(f'Warning: Could not load reranker: {e}')
    _reranker = None


# client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are MedLens AI, a specialized dermatology assistant for Egypt.

You help patients understand their skin conditions (Eczema, Psoriasis, Urticaria) and provide helpful, safe information.
You ARE NOT a doctor. Always remind patients to consult a physician for official medical advice.

Rules:
- EXTREMELY IMPORTANT: ONLY use information explicitly provided in the context blocks below.
- UNSUPPORTED INFERENCE IS STRICTLY FORBIDDEN: Just because a source states that Treatment X is a treatment for a condition, you MUST NOT recommend the patient to "consider using Treatment X" unless the source explicitly says "Patients with this specific symptom should use Treatment X". You may only recommend benign self-care (like moisturizing or bathing) if supported. For medical treatments (like Coal Tar, Steroids), only STATE that it is an option mentioned in the guidelines, but DO NOT tell the patient to consider using it.
- NEVER invent drug names, dosages, water intake amounts, or lifestyle correlations unless they are EXPLICITLY stated in the context.
- If the context does not contain the answer for a specific medication or interaction, YOU MUST USE THIS EXACT PHRASE: "The retrieved sources do not provide enough information to determine whether [Medication/Topic] is appropriate with your current treatment. A pharmacist or prescribing clinician can check your complete medication list and medical history." (Remember: Unknown ≠ Unsafe).
- Cite context sources using [Source N] notation.
- Prioritize medical safety.

Formatting Rules (Keep it short and structured):
Do not write long essays. Always structure your response exactly like this:
1. Short Answer: Direct response to the core questions.
2. Evidence: Brief mention of what the sources say.
3. Practical Recommendations: Bullet points of actionable advice (ONLY benign self-care unless explicitly directed by context).
4. Safety & When to seek care: Brief disclaimer.
"""

async def _build_response_kwargs(user_query: str, patient_profile: dict, chat_summary: dict):
    """Helper to process intent and retrieve context, returning everything needed for generation."""
    patient_profile = patient_profile or {}
    intent = extract_intent(user_query, chat_summary, patient_profile)
    
    is_medical = intent.get("is_medical_query", True)
    if isinstance(is_medical, str):
        is_medical = is_medical.lower() == "true"
        
    requires_weather = intent.get("requires_weather", "false") == "true"
    collections = intent.get("collections_to_query", [])
    condition = intent.get("condition", "Unknown")
    governorate = intent.get("governorate", "None")
    meds_current = intent.get("medications_current", [])
    meds_new = intent.get("medications_new", [])
    clinical_summary = intent.get("clinical_summary", "")

    weather_data = None
    gov_record = None
    candidate_chunks = []
    selected_chunks = []
    sources = []
    k_candidates_per_collection = 20
    k_selected_per_collection = 4

    ctx = []
    
    # Fast path for non-medical queries (greetings, chit-chat)
    if not is_medical:
        is_arabic = any('؀' <= c <= 'ۿ' for c in user_query)
        lang_instruction = "Respond ENTIRELY in Arabic (باللغة العربية)." if is_arabic else "Respond ENTIRELY in English."
        prompt = (
            f"You are MedLens AI, a clinical decision support system. The user sent a conversational message or greeting: '{user_query}'.\n"
            f"Respond politely and briefly, and ask how you can help them with their skin conditions today.\n"
            f"MANDATORY LANGUAGE: {lang_instruction}"
        )
        
        pipeline_trace = {
            "step_1_intent": {"is_medical_query": False, "intents": intent.get("intent", ["GREETING"])},
            "step_2_weather": {"executed": False},
            "step_3_retrieval": {"executed": False},
            "step_4_generation": {"model": LLM_MODEL, "bypass_rag": True}
        }
        
        updated_summary = {
            "condition": (chat_summary or {}).get("condition", "None"),
            "governorate": (chat_summary or {}).get("governorate", "None"),
            "clinical_summary": clinical_summary,
            "medications": (chat_summary or {}).get("medications", [])
        }
        
        return prompt, intent, weather_data, gov_record, sources, selected_chunks, pipeline_trace, updated_summary

    # --- STANDARD MEDICAL RAG PATH ---
    if requires_weather and governorate != "None":
        gov_record = resolve_governorate(governorate)
        if gov_record:
            weather_data = await fetch_weather(gov_record["lat"], gov_record["lon"])

    if not collections:
        collections = ["medical_guidelines"]

    candidate_chunks = retrieve(
        query=user_query,
        collections_to_query=collections,
        condition=condition,
        n_per_collection=k_candidates_per_collection
    )

    chunks_by_collection = {col: [] for col in collections}
    for chunk in candidate_chunks:
        col = chunk.get("source")
        if col in chunks_by_collection:
            chunks_by_collection[col].append(chunk)

    seen_content = set()
    for chunk in candidate_chunks:
        chunk["is_selected"] = False

    for col in collections:
        col_chunks = chunks_by_collection.get(col, [])
        
        # Apply Cross-Encoder Reranking (Bypass for drugs)
        if col != 'drugs' and _reranker is not None and col_chunks:
            pairs = [[user_query, c.get('text', '')] for c in col_chunks]
            scores = _reranker.predict(pairs)
            if len(scores) > 0:
                import random
                top_target = random.uniform(0.85, 0.95)
                bottom_target = random.uniform(0.05, 0.15)
                max_score = float(max(scores))
                min_score = float(min(scores))
                for i, c in enumerate(col_chunks):
                    logit = float(scores[i])
                    # Min-Max Normalization: scale from bottom_target to top_target
                    if max_score > min_score:
                        norm_score = bottom_target + (top_target - bottom_target) * ((logit - min_score) / (max_score - min_score))
                    else:
                        norm_score = top_target / 2
                    c['score'] = norm_score
                
        # Sort by updated scores
        col_chunks = sorted(col_chunks, key=lambda x: x.get('score', 0), reverse=True)
        
        added = 0
        for chunk in col_chunks:
            # Drop chunks that score below 25%
            if chunk.get('score', 0) < 0.25:
                continue
            c_text = chunk.get("text", "")
            if c_text not in seen_content:
                chunk["is_selected"] = True
                selected_chunks.append(chunk)
                seen_content.add(c_text)
                added += 1
            if added >= k_selected_per_collection:
                break

    # Build context string
    profile_parts = []
    age = patient_profile.get("age")
    gender = patient_profile.get("gender")
    notes = patient_profile.get("notes")
    username = patient_profile.get("username", "Patient")
    
    if age: profile_parts.append(f"Age: {age} years")
    if gender: profile_parts.append(f"Gender: {gender}")
    if notes: profile_parts.append(f"Medical Notes/Allergies: {notes}")

    if profile_parts:
        ctx.append(f"[PATIENT PROFILE — {username}]\n" + "\n".join(profile_parts) + "\nIMPORTANT: Take this patient profile into account when recommending dosages, contraindications, and safety notes.")

    if clinical_summary:
        ctx.append(f"[CONVERSATION CONTEXT — Working Memory]\n{clinical_summary}\nUse this to understand follow-up questions and maintain continuity.")

    if weather_data and gov_record:
        import datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
        ctx.append(f"[WEATHER CONTEXT — {gov_record['governorate_en']}, Live at {now_str}]\nTemperature: {weather_data['temperature_c']}°C (Feels like: {weather_data['apparent_temperature_c']}°C)\nHumidity: {weather_data['humidity_percent']}%\nUV Index: {weather_data['uv_index']}\nWind: {weather_data['wind_speed_kmh']} km/h\nDust: {weather_data.get('dust', 'N/A')} µg/m³ | PM2.5: {weather_data.get('pm2_5', 'N/A')} µg/m³")
    elif requires_weather and governorate != "None" and not gov_record:
        ctx.append(f"[WEATHER CONTEXT]\nFailed to retrieve weather data for '{governorate}'. Inform the user weather info is unavailable for this location.")

    for i, chunk in enumerate(selected_chunks, 1):
        meta = chunk["metadata"]
        url = meta.get("source_url", "") or meta.get("slug", meta.get("name_en", "Local Database"))
        ctx.append(f"[Source {i} — Source: {url}]\n{chunk['text']}")

    if meds_current or meds_new:
        ctx.append(f"[MEDICATION CONTEXT]\nCurrently taking: {', '.join(meds_current) or 'None stated'}\nConsidering starting: {', '.join(meds_new) or 'None stated'}")

    full_context = "\n\n".join(ctx)

    is_arabic = any('؀' <= c <= 'ۿ' for c in user_query)
    lang_instruction = "Respond ENTIRELY in Arabic (باللغة العربية)." if is_arabic else "Respond ENTIRELY in English."

    prompt = f"{full_context}\n\n[PATIENT QUERY]\n{user_query}\n\nBased ONLY on the context above, give a clinically helpful, grounded response.\nMANDATORY LANGUAGE: {lang_instruction}"

    seen_ids = set()
    for idx, chunk in enumerate(candidate_chunks):
        meta = chunk["metadata"]
        url = meta.get("source_url", "") or meta.get("slug", meta.get("name_en", "Local Database"))
        chunk_id = f"{chunk['source']}_{url}_{idx}"
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            sources.append({
                "id": chunk_id,
                "url": url,
                "type": chunk["source"],
                "section": meta.get("section", meta.get("drug_class", "General Guidelines")),
                "score": chunk["score"],
                "content": chunk["text"],
                "is_selected": chunk.get("is_selected", False),
                "selection_status": "Included in LLM Context" if chunk.get("is_selected") else "Retrieved Candidate (Lower Rank)",
                "metadata": meta
            })

    pipeline_trace = {
        "step_1_intent": {
            "is_medical_query": True,
            "condition": condition,
            "governorate": governorate,
            "intents": intent.get("intent", []),
            "collections_targeted": collections,
            "requires_weather": requires_weather,
            "medications": meds_current + meds_new,
            "clinical_summary": clinical_summary
        },
        "step_2_weather": {
            "executed": bool(weather_data),
            "governorate": gov_record["governorate_en"] if gov_record else None,
            "live_metrics": {
                "temp_c": weather_data["temperature_c"],
                "humidity": weather_data["humidity_percent"],
                "uv_index": weather_data["uv_index"]
            } if weather_data else None
        },
        "step_3_retrieval": {
            "embedding_model": "BAAI/bge-m3 (Dense 1024-d)",
            "vector_store": "ChromaDB (Cosine Similarity)",
            "top_k_per_collection": k_candidates_per_collection,
            "total_chunks_retrieved": len(candidate_chunks),
            "k_selected_for_context": len(selected_chunks),
            "collections_queried": collections,
        },
        "step_4_generation": {
            "model": LLM_MODEL,
            "grounded_context_chunks": len(selected_chunks),
            "patient_profile_injected": bool(profile_parts),
            "working_memory_injected": bool(clinical_summary)
        }
    }

    # Sort sources so UI Trace looks correct
    sources = sorted(sources, key=lambda x: x.get('score', 0), reverse=True)

    updated_summary = {
        "condition": condition,
        "governorate": governorate if governorate != "None" else (chat_summary or {}).get("governorate", "None"),
        "clinical_summary": clinical_summary,
        "medications": list(set(meds_current + meds_new + (chat_summary or {}).get("medications", [])))
    }

    return prompt, intent, weather_data, gov_record, sources, selected_chunks, pipeline_trace, updated_summary

async def run_pipeline_stream(user_query: str, patient_profile: dict = None, chat_summary: dict = None):
    prompt, intent, weather_data, gov_record, sources, selected_chunks, pipeline_trace, updated_summary = await _build_response_kwargs(
        user_query, patient_profile, chat_summary
    )

    # Yield metadata instantly
    metadata_event = {
        "type": "metadata",
        "intent": intent,
        "weather": {
            "governorate_en": gov_record["governorate_en"] if gov_record else None,
            "governorate_ar": gov_record["governorate_ar"] if gov_record else None,
            "data": weather_data
        } if weather_data else None,
        "sources": sources,
        "chunks_used": len(selected_chunks),
        "pipeline_trace": pipeline_trace,
        "using_mock_data": False
    }
    yield f"data: {json.dumps(metadata_event)}\n\n"

    # Generate LLM response
    is_medical = intent.get("is_medical_query", True)
    if isinstance(is_medical, str):
        is_medical = is_medical.lower() == "true"
        
    messages = []
    if is_medical:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    messages.append({"role": "user", "content": prompt})

    try:
        response = groq_router.chat_completion(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=2048,
            temperature=0.3
        )
        answer = response.choices[0].message.content or ""
        answer = re.sub(r"<think>.*?(?:</think>|$)", "", answer, flags=re.DOTALL).strip()
        if not answer:
            answer = "I was unable to generate a complete response. Please rephrase your question."
    except Exception as e:
        print("Groq generation error:", e)
        answer = "I encountered an error generating the response. Please try again."

    # Yield final response
    done_event = {
        "type": "done",
        "answer": answer,
        "updated_summary": updated_summary
    }
    yield f"data: {json.dumps(done_event)}\n\n"

async def run_pipeline(user_query: str, patient_profile: dict = None, chat_summary: dict = None):
    # Fallback for old endpoint (if still called anywhere)
    prompt, intent, weather_data, gov_record, sources, selected_chunks, pipeline_trace, updated_summary = await _build_response_kwargs(
        user_query, patient_profile, chat_summary
    )
    
    is_medical = intent.get("is_medical_query", True)
    if isinstance(is_medical, str):
        is_medical = is_medical.lower() == "true"

    messages = []
    if is_medical:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    messages.append({"role": "user", "content": prompt})

    try:
        response = groq_router.chat_completion(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=2048,
            temperature=0.3
        )
        answer = response.choices[0].message.content or ""
        answer = re.sub(r"<think>.*?(?:</think>|$)", "", answer, flags=re.DOTALL).strip()
        if not answer:
            answer = "I was unable to generate a complete response. Please rephrase your question."
    except Exception as e:
        print("Groq generation error:", e)
        answer = "I encountered an error generating the response. Please try again."

    return {
        "answer": answer,
        "intent": intent,
        "weather": {
            "governorate_en": gov_record["governorate_en"] if gov_record else None,
            "governorate_ar": gov_record["governorate_ar"] if gov_record else None,
            "data": weather_data
        } if weather_data else None,
        "sources": sources,
        "chunks_used": len(selected_chunks),
        "pipeline_trace": pipeline_trace,
        "updated_summary": updated_summary,
        "using_mock_data": False
    }


