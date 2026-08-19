"""
Smart Merger & Cleaner for Egyptian Drug Datasets:
1. mahmoudfalous/eg-drugs (26K+ drugs with FDA warnings, Arabic usage, barcodes)
2. karem505/egyptian-drug-database (25K+ drugs with routes, drug classes, manufacturers)

Cleans & Produces:
- drugs/unified_egyptian_drugs.json (Cleaned, Deduplicated, Price-free)
"""

import json
import re
import os
from collections import defaultdict

def canonical_key(s):
    if not s:
        return ""
    s = s.lower()
    # Normalize dosage units (e.g. '500 mg' -> '500mg', '1 gm' -> '1gm')
    s = re.sub(r'(\d+(?:\.\d+)?)\s*(mg|gm|g|ml|mcg|iu|%)\b', r'\1\2', s)
    # Normalize dosage forms & packaging terms to canonical tokens
    s = re.sub(r'\b(f\.?c\.?\s*tablets?|f\.?c\.?\s*tabs?|fctabs?|fctab|tablets?|tabs?|tab)\b', 'tab', s)
    s = re.sub(r'\b(f\.?c\.?\s*capsules?|f\.?c\.?\s*caps?|fccaps?|capsules?|caps?|cap)\b', 'cap', s)
    s = re.sub(r'\b(ampoules?|ampules?|amps?|amp)\b', 'amp', s)
    s = re.sub(r'\b(vials?|vial)\b', 'vial', s)
    s = re.sub(r'\b(syrups?|syr)\b', 'syr', s)
    s = re.sub(r'\b(suspensions?|susp)\b', 'susp', s)
    s = re.sub(r'\b(sachets?|sachet)\b', 'sachet', s)
    s = re.sub(r'\b(suppositories?|suppos?|supps?|supp)\b', 'supp', s)
    s = re.sub(r'\b(ointments?|oints?|oint)\b', 'oint', s)
    s = re.sub(r'\b(creams?|crm)\b', 'cream', s)
    s = re.sub(r'\b(solutions?|soln?|sol)\b', 'sol', s)
    # Remove all non-alphanumeric characters
    s = re.sub(r'[^a-z0-9]', '', s)
    return s

def clean_active_key(s):
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'\(.*?\)', '', s)
    s = re.sub(r'[^a-z]', '', s)
    return s

def clean_arabic_name(ar):
    if not ar or not isinstance(ar, str):
        return None
    s = ar.strip()
    # Remove trailing slashes, dots, dashes, colons
    s = re.sub(r'[\s/\\.\-:]+$', '', s)
    # Remove orphaned slash numbers like '/ 3 ./' or '/ 10'
    s = re.sub(r'/\s*\d+\s*[\./]*', '', s)
    # Fix transliteration artifacts
    s = re.sub(r'\bفاج\.?\s*سوبب\b', 'لبوس مهبلي', s)
    s = re.sub(r'\bسوبب\b', 'لبوس', s)
    s = re.sub(r'\bتابس\b', 'أقراص', s)
    s = re.sub(r'\bسيرب\b', 'شراب', s)
    s = re.sub(r'\bسسبنشن\b', 'معلق', s)
    s = re.sub(r'[\s/\\.\-:]+$', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    if s in [".", "-", "/", "", "None", "null"]:
        return None
    return s

def clean_text(s, empty_placeholders=None):
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if empty_placeholders and s in empty_placeholders:
        return None
    if s in [".", "-", "", "None", "null"]:
        return None
    return s

def clean_uses_text(u):
    if not u or not isinstance(u, str):
        return None
    s = u.strip()
    bad_placeholders = [
        "لا توجد دواعي استعمال مسجلة.", "لا يوجد دواعي استعمال مسجلة",
        "No uses recorded.", "No use recorded.", "No registered indications.", "."
    ]
    if s in bad_placeholders:
        return None
    
    # Filter out scraped FDA noise patterns that were falsely attached to supplements/unrelated items
    bad_signatures = [
        r'reduces underarm wetness',
        r'for the temporary relief of itchy, painful, red, or irrita',
        r'Helps prevent diaper rash',
        r'Use temporary relieves: ■ cough due to cold'
    ]
    for sig in bad_signatures:
        if re.search(sig, s, re.IGNORECASE):
            return None
            
    return s

def generate_slug(name):
    if not name:
        return "drug"
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-+', '-', s)
    s = s.strip('-')
    return s or "drug"

def run_merge():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, "..", "..", ".."))
    raw_drugs_dir = os.path.join(project_root, "data", "raw", "Drugs")
    
    path1_json = os.path.join(raw_drugs_dir, "eg_drugs_raw.json")
    path2_json = os.path.join(raw_drugs_dir, "egyptian_drugs_raw.json")

    out_json = os.path.join(raw_drugs_dir, "unified_egyptian_drugs.json")

    print("Loading Dataset 1 (mahmoudfalous/eg-drugs)...")
    with open(path1_json, "r", encoding="utf-8") as f:
        data1 = json.loads(f.read(), strict=False)
    print(f"Loaded {len(data1)} records from Dataset 1.")

    print("Loading Dataset 2 (karem505/egyptian-drug-database)...")
    with open(path2_json, "r", encoding="utf-8") as f:
        data2 = json.load(f)
    print(f"Loaded {len(data2)} records from Dataset 2.")

    # 1. Index Dataset 1 by canonical key & active ingredient
    d1_canonical = {}
    d1_fuzzy = defaultdict(list)
    for item in data1:
        name = item.get("name", "")
        ck = canonical_key(name)
        if ck and ck not in d1_canonical:
            d1_canonical[ck] = item
        
        act_k = clean_active_key(item.get("active"))
        if act_k:
            d1_fuzzy[act_k].append(item)

    # 2. Match Dataset 2 & Dataset 1
    matched_d1_ids = set()
    raw_pairs = [] # (item1, item2)

    for item2 in data2:
        name2 = item2.get("commercial_name_en", "")
        ck2 = canonical_key(name2)
        
        item1 = None
        if ck2 in d1_canonical:
            item1 = d1_canonical[ck2]
        
        if item1 is not None:
            matched_d1_ids.add(item1.get("id"))
            raw_pairs.append((item1, item2))
        else:
            raw_pairs.append((None, item2))

    # Add remaining unmatched records from Dataset 1
    for item1 in data1:
        if item1.get("id") not in matched_d1_ids:
            raw_pairs.append((item1, None))

    print(f"Initial raw pairs: {len(raw_pairs)}")

    # 3. Consolidate and Deduplicate into Clean Unified Records
    consolidated = {} # (canonical_name_key, clean_active_key) -> record

    for item1, item2 in raw_pairs:
        raw_name_en = (item2.get("commercial_name_en") if item2 else (item1.get("name") if item1 else "")).strip()
        
        # Clean Arabic name: prefer Dataset 1's authentic name if available
        raw_name_ar = None
        if item1 and item1.get("arabic"):
            raw_name_ar = clean_arabic_name(item1.get("arabic"))
        if not raw_name_ar and item2 and item2.get("commercial_name_ar"):
            raw_name_ar = clean_arabic_name(item2.get("commercial_name_ar"))

        # Active Ingredients
        active = clean_text(item2.get("scientific_name") if item2 and item2.get("scientific_name") else (item1.get("active") if item1 else None))
        if active:
            active = active.upper()

        # Drug Class
        drug_class = clean_text(item2.get("drug_class") if item2 and item2.get("drug_class") else (item1.get("description") if item1 else None), ["."])
        if drug_class:
            drug_class = drug_class.upper()

        # Route
        route = clean_text(item2.get("route") if item2 else None, ["UNKNOWN", "."])
        if route:
            route = route.upper()

        # Manufacturer
        manufacturer = clean_text(item2.get("manufacturer") if item2 and item2.get("manufacturer") else (item1.get("company") if item1 else None), ["."])

        # Uses
        uses_ar = clean_uses_text(item1.get("uses_summary") if item1 else None)
        uses_en = clean_uses_text(item1.get("uses_summary_en") if item1 else None)
        
        # Fix misassigned anesthetic text for blood factors
        if active and "FACTOR VII" in active and uses_ar and "مخدر" in uses_ar:
            uses_ar = None

        # Safety Warnings
        safety_warnings = None
        if item1:
            safety_warnings = {
                "pregnancy": bool(item1.get("warning_pregnancy")),
                "lactation": bool(item1.get("warning_lactation")),
                "hypertension": bool(item1.get("warning_high_blood_pressure")),
                "diabetes": bool(item1.get("warning_diabetes")),
                "kidney": bool(item1.get("warning_kidney")),
                "liver": bool(item1.get("warning_liver")),
                "heart": bool(item1.get("warning_heart")),
            }

        warnings_summary_ar = clean_text(item1.get("warnings_summary") if item1 else None, ["لا توجد تحذيرات مسجلة."])
        warnings_summary_en = clean_text(item1.get("warnings_summary_en") if item1 else None, ["No warnings recorded."])

        # Barcode
        barcode = clean_text(str(item1.get("barcode")) if item1 and item1.get("barcode") else None, ["None", "null", ""])

        # Sources
        sources = set()
        if item1:
            sources.add("mahmoudfalous/eg-drugs")
        if item2:
            sources.add("karem505/egyptian-drug-database")

        ck = canonical_key(raw_name_en)
        act_k = clean_active_key(active)
        dedup_key = (ck, act_k)

        if dedup_key not in consolidated:
            consolidated[dedup_key] = {
                "name_en": raw_name_en.upper(),
                "name_ar": raw_name_ar,
                "active_ingredients": active,
                "drug_class": drug_class,
                "route": route,
                "manufacturer": manufacturer,
                "uses_ar": uses_ar,
                "uses_en": uses_en,
                "safety_warnings": safety_warnings,
                "warnings_summary_ar": warnings_summary_ar,
                "warnings_summary_en": warnings_summary_en,
                "barcode": barcode,
                "sources": sources
            }
        else:
            # Merge fields cleanly into single record
            curr = consolidated[dedup_key]
            if not curr["name_ar"] and raw_name_ar:
                curr["name_ar"] = raw_name_ar
            if not curr["drug_class"] and drug_class:
                curr["drug_class"] = drug_class
            if not curr["route"] and route:
                curr["route"] = route
            if not curr["manufacturer"] and manufacturer:
                curr["manufacturer"] = manufacturer
            if not curr["uses_ar"] and uses_ar:
                curr["uses_ar"] = uses_ar
            if not curr["uses_en"] and uses_en:
                curr["uses_en"] = uses_en
            if not curr["barcode"] and barcode:
                curr["barcode"] = barcode
            if not curr["safety_warnings"] and safety_warnings:
                curr["safety_warnings"] = safety_warnings
            if not curr["warnings_summary_ar"] and warnings_summary_ar:
                curr["warnings_summary_ar"] = warnings_summary_ar
            if not curr["warnings_summary_en"] and warnings_summary_en:
                curr["warnings_summary_en"] = warnings_summary_en
            curr["sources"].update(sources)

    print(f"Total consolidated unique drugs: {len(consolidated)}")

    # 4. Generate Unique Slugs & Finalize Schema
    final_records = []
    slug_counts = {}

    for (ck, act_k), rec in consolidated.items():
        base_slug = generate_slug(rec["name_en"])
        if base_slug in slug_counts:
            slug_counts[base_slug] += 1
            slug = f"{base_slug}-{slug_counts[base_slug]}"
        else:
            slug_counts[base_slug] = 1
            slug = base_slug

        record = {
            "slug": slug,
            "name_en": rec["name_en"],
            "name_ar": rec["name_ar"],
            "active_ingredients": rec["active_ingredients"],
            "drug_class": rec["drug_class"],
            "route": rec["route"],
            "manufacturer": rec["manufacturer"],
            "uses_ar": rec["uses_ar"],
            "uses_en": rec["uses_en"],
            "safety_warnings": rec["safety_warnings"],
            "warnings_summary_ar": rec["warnings_summary_ar"],
            "warnings_summary_en": rec["warnings_summary_en"],
            "barcode": rec["barcode"],
            "sources": sorted(list(rec["sources"]))
        }
        final_records.append(record)

    # Sort alphabetically by English name
    final_records.sort(key=lambda x: x["name_en"])

    # 5. Write to JSON
    print(f"\nWriting clean unified JSON to: {out_json}")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(final_records, f, ensure_ascii=False, indent=2)



    print(f"\n Master Clean Egyptian Drug Database Generated Successfully!")
    print(f"- Total Clean Drugs: {len(final_records)}")
    print(f"- JSON File Size: {os.path.getsize(out_json) / (1024*1024):.2f} MB")

if __name__ == "__main__":
    run_merge()
