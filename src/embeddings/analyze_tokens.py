import json
import numpy as np
from pathlib import Path
from transformers import AutoTokenizer

def analyze_tokens():
    print("Loading tokenizer BAAI/bge-m3...")
    tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-m3")
    
    data_path = Path("data/processed/drugs_document/drugs_documents.json").resolve()
    print(f"Reading processed documents from {data_path}")
    
    with open(data_path, "r", encoding="utf-8") as f:
        documents = json.load(f)
        
    token_counts = []
    
    print(f"Tokenizing {len(documents)} documents...")
    for doc in documents:
        text = doc.get("page_content", "")
        # Don't add special tokens if we are just counting raw length, but standard tokenization adds them.
        # We can just count standard tokens.
        tokens = tokenizer(text, truncation=False, add_special_tokens=True)["input_ids"]
        token_counts.append(len(tokens))
        
    token_counts = np.array(token_counts)
    
    stats = {
        "total_documents": len(token_counts),
        "total_tokens": int(np.sum(token_counts)),
        "average_tokens": float(np.mean(token_counts)),
        "median_tokens": float(np.median(token_counts)),
        "min_tokens": int(np.min(token_counts)),
        "max_tokens": int(np.max(token_counts)),
        "p75": float(np.percentile(token_counts, 75)),
        "p90": float(np.percentile(token_counts, 90)),
        "p95": float(np.percentile(token_counts, 95)),
        "p99": float(np.percentile(token_counts, 99))
    }
    
    print("\n--- Token Statistics ---")
    for k, v in stats.items():
        print(f"{k}: {v}")
        
    out_path = Path("token_statistics.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)
    print(f"\nSaved stats to {out_path.resolve()}")

if __name__ == "__main__":
    analyze_tokens()
