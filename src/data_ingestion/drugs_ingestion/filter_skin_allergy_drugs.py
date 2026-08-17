"""
filter_skin_allergy_drugs.py
============================
Filters Egyptian drug database to keep only drugs relevant to:
  - Atopic Dermatitis (Eczema)
  - Psoriasis
  - Urticaria / Hives
  - Skin allergy / dermatology domain

Output: skin_allergy_drugs.json  (full drug objects, not names only)

Usage:
    python filter_skin_allergy_drugs.py
    python filter_skin_allergy_drugs.py --input path/to/drugs.json --output path/to/out.json
"""

import json
import argparse
from pathlib import Path

# ── 1. Domain keyword lists ────────────────────────────────────────────────────

# Keywords matched against drug_class (lowercase)
DRUG_CLASS_KEYWORDS = [
    # Antihistamines — core treatment for urticaria + allergy symptoms
    "antihistamine", "anti-histamine", "anti histamine",
    "antihistaminic", "anti-histaminic",
    "anti-allerg", "antiallerg", "anti allerg",
    "antipruritic", "anti-pruritic",
    "mast cell",

    # Corticosteroids / Glucocorticoids — eczema & psoriasis flare treatment
    "glucocorticoid", "corticosteroid",

    # Immunosuppressants — severe eczema / psoriasis (cyclosporine, methotrexate…)
    "immunosupp", "immunosuppressive", "immunosuppressent",

    # Topical dermatologicals — emollients, moisturisers, skin barriers
    "emollient", "moistur", "soothing",
    "skin care", "skin care.", "skincare",
    "topical emollient", "topical care",

    # Antifungals — secondary fungal infections in eczema
    "antifungal", "anti-fungal",

    # Wound / burn healing — scratching complications in eczema
    "wound healing", "wound care", "wound cream",
    "burn healing", "burns",

    # Sun protection — UV is a major psoriasis / eczema trigger
    "sunscreen", "sun block", "sunblock",

    # Anti-acne (same dermatology domain)
    "anti-acne", "anti acne", "acne",

    # Skin-care product lines
    "anti-eczematous",
    "skin emollient",
    "skin moistur",
    "skin sooth",
    "protective skin barrier",
]

# Keywords matched against active_ingredients (lowercase)
# Catches drugs regardless of how drug_class was labeled
ACTIVE_INGREDIENT_KEYWORDS = [
    # Antihistamines
    "cetirizine", "loratadine", "fexofenadine", "hydroxyzine",
    "chlorpheniramine", "diphenhydramine", "desloratadine",
    "levocetirizine", "rupatadine", "bilastine", "ebastine",
    "ketotifen", "azelastine", "olopatadine",

    # Topical / systemic corticosteroids
    "hydrocortisone", "betamethasone", "clobetasol", "mometasone",
    "triamcinolone", "fluticasone", "prednisolone", "methylprednisolone",
    "dexamethasone", "fluocinolone", "desonide", "budesonide",

    # Calcineurin inhibitors (eczema — non-steroidal)
    "tacrolimus", "pimecrolimus",

    # PDE4 inhibitors (eczema)
    "crisaborole", "roflumilast", "apremilast",

    # JAK inhibitors (eczema / psoriasis)
    "baricitinib", "upadacitinib", "abrocitinib", "ruxolitinib",
    "tofacitinib",

    # Biologics (psoriasis / eczema)
    "dupilumab", "secukinumab", "ixekizumab", "guselkumab",
    "risankizumab", "adalimumab", "etanercept", "ustekinumab",
    "lebrikizumab", "tralokinumab", "nemolizumab",

    # Immunosuppressants
    "cyclosporine", "methotrexate", "azathioprine", "mycophenolate",

    # Retinoids (psoriasis)
    "acitretin", "isotretinoin", "tretinoin", "adapalene",

    # Vitamin D analogues (psoriasis)
    "calcipotriol", "calcitriol", "calcipotriene",

    # Coal tar (psoriasis)
    "coal tar",

    # Topical antibiotics (secondary bacterial infections in eczema)
    "mupirocin", "fusidic acid", "neomycin", "bacitracin",
    "chloramphenicol", "gentamicin", "erythromycin",

    # Topical antifungals (secondary fungal infections)
    "clotrimazole", "miconazole", "ketoconazole", "econazole",
    "terbinafine", "nystatin", "fluconazole",

    # Emollients / moisturisers
    "urea", "glycerol", "glycerin", "petrolatum", "paraffin",
    "ceramide", "hyaluronic acid", "lactic acid",

    # Phototherapy adjunct
    "methoxsalen", "psoralen",

    # Zinc (wound healing / barrier)
    "zinc oxide",
]


# ── 2. Filter logic ────────────────────────────────────────────────────────────

def is_skin_allergy_drug(drug: dict) -> bool:
    """Return True if the drug is relevant to skin / allergy domain."""

    drug_class = (drug.get("drug_class") or "").strip().lower()
    ingredients = (drug.get("active_ingredients") or "").strip().lower()
    uses = (drug.get("uses_en") or "").strip().lower()

    # Match drug_class
    if any(kw in drug_class for kw in DRUG_CLASS_KEYWORDS):
        return True

    # Match active_ingredients
    if any(kw in ingredients for kw in ACTIVE_INGREDIENT_KEYWORDS):
        return True

    # Extra safety net: catch eczema / psoriasis / urticaria in uses text
    for condition_kw in ("eczema", "psoriasis", "urticaria", "atopic dermatitis",
                          "dermatitis", "pruritus", "skin rash", "hives"):
        if condition_kw in uses:
            return True

    return False


# ── 3. Main ────────────────────────────────────────────────────────────────────

def main(input_path: str, output_path: str) -> None:
    print(f"📂 Reading: {input_path}")

    with open(input_path, encoding="utf-8") as f:
        all_drugs = json.load(f)

    total = len(all_drugs)
    print(f"   Total drugs in DB: {total:,}")

    skin_drugs = [d for d in all_drugs if is_skin_allergy_drug(d)]
    filtered = len(skin_drugs)

    print(f"\n✅ Drugs matching skin/allergy domain: {filtered:,}")
    print(f"   Removed (irrelevant):               {total - filtered:,}")
    print(f"   Reduction:                           {(total - filtered) * 100 // total}%")

    # --- breakdown by drug_class (top 30) ---
    from collections import Counter
    class_counts = Counter(
        (d.get("drug_class") or "").strip().upper()
        for d in skin_drugs
    )
    print("\n📊 Top drug classes in filtered set:")
    for cls, count in class_counts.most_common(30):
        print(f"   {count:4d}  {cls}")

    # --- save output ---
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w", encoding="utf-8") as f:
        json.dump(skin_drugs, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Saved to: {out.resolve()}")
    print(f"   File size: {out.stat().st_size / 1024 / 1024:.2f} MB")


# ── 4. Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Base directory = folder containing this script (works from any working directory)
    SCRIPT_DIR = Path(__file__).parent.resolve()

    parser = argparse.ArgumentParser(description="Filter Egyptian drugs for skin/allergy domain")
    parser.add_argument(
        "--input",
        default=str(SCRIPT_DIR / "unified_egyptian_drugs.json"),
        help="Path to unified_egyptian_drugs.json (default: same folder as script)"
    )
    parser.add_argument(
        "--output",
        default=str(SCRIPT_DIR / "skin_allergy_drugs.json"),
        help="Output path for filtered JSON (default: same folder as script)"
    )
    args = parser.parse_args()
    main(args.input, args.output)
