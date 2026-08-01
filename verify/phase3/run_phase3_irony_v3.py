"""Execute Phase 3 v3 Irony Inference and WP3 T3.2.

Runs cardiffnlp/twitter-roberta-base-irony on all v3 rows, computes
profile stats, and samples 15 rows for the human seed set.
Marks T3.3 and T3.4 as blocked since we don't have a Gemini API key.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.phase1_ingestion.storage_serializers_view import StorageSerializersView
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_ID = "cardiffnlp/twitter-roberta-base-irony"

def run_phase3_irony(project_root: str | Path = ".") -> None:
    root = Path(project_root).resolve()
    p3_dir = root / "data" / "02_interim" / "phase3_v3"
    shard_dir = p3_dir / "_irony_shards"
    shard_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir = root / "output" / "results" / "phase3" / "v3" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    anno_dir = root / "data" / "04_annotations"
    anno_dir.mkdir(parents=True, exist_ok=True)

    serializer = StorageSerializersView()
    sentiment_path = p3_dir / "twitter_sentiment_v3.parquet"
    if not sentiment_path.exists():
        raise FileNotFoundError("Sentiment parquet missing. Run Phase 3 v3 first.")

    df = pd.read_parquet(sentiment_path)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID).to(device).eval()
    
    if device == "cuda":
        model = model.half()
    
    torch.set_num_threads(os.cpu_count())
    batch_size = 128 if device == "cuda" else 64
    max_length = 128
    
    chunk_size = 50000
    import math
    num_shards = math.ceil(len(df) / chunk_size)
    
    results = []
    total_scored = 0
    label_map = {0: "non_irony", 1: "irony"}
    
    df["_token_len"] = df["roberta_input_text"].str.len()
    
    t0 = time.time()
    
    with torch.inference_mode():
        for i in range(num_shards):
            shard_path = shard_dir / f"shard_{i}.parquet"
            if shard_path.exists():
                shard_df = pd.read_parquet(shard_path)
                results.append(shard_df)
                total_scored += len(shard_df)
                continue
                
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, len(df))
            
            chunk = df.iloc[start_idx:end_idx].copy()
            chunk_sorted = chunk.sort_values(by="_token_len").copy()
            inputs = chunk_sorted["roberta_input_text"].tolist()
            
            shard_results = []
            j = 0
            while j < len(inputs):
                batch_texts = inputs[j:j+batch_size]
                try:
                    encodings = tokenizer(batch_texts, padding=True, truncation=True, max_length=max_length, return_tensors="pt").to(device)
                    outputs = model(**encodings)
                    probs = torch.nn.functional.softmax(outputs.logits, dim=-1).float().cpu().numpy()
                    
                    for p in probs:
                        prob_irony = float(p[1])
                        lbl = label_map[int(np.argmax(p))]
                        shard_results.append({
                            "irony_prob": prob_irony,
                            "irony_label": lbl,
                            "irony_model_status": "completed"
                        })
                    j += batch_size
                except torch.cuda.OutOfMemoryError:
                    if batch_size > 16:
                        batch_size //= 2
                        torch.cuda.empty_cache()
                    else:
                        raise
            
            res_df_sorted = pd.DataFrame(shard_results, index=chunk_sorted.index)
            res_df = res_df_sorted.loc[chunk.index]
            
            for col in res_df.columns:
                chunk[col] = res_df[col]
                
            chunk.to_parquet(shard_path)
            results.append(chunk)
            total_scored += len(chunk)
            
            if (i+1) % 5 == 0:
                print(f"Processed {total_scored}/{len(df)} tweets for irony...")
                
    wall_clock = time.time() - t0
    final_df = pd.concat(results, axis=0)
    final_df = final_df.loc[df.index]
    
    # Check old heuristic exists
    if "sarcasm_risk_score" in final_df.columns:
        final_df["sarcasm_risk_heuristic"] = final_df["sarcasm_risk_score"]
        
    final_df = final_df.drop(columns=["_token_len"])
    
    # Save parquet
    serializer.serialize_to_parquet(final_df, sentiment_path)
    
    # Compute profile
    if "sarcasm_risk_heuristic" in final_df.columns:
        mask = final_df["sarcasm_risk_heuristic"].notna() & final_df["irony_prob"].notna()
        if mask.sum() > 0:
            pearson_r, _ = stats.pearsonr(final_df.loc[mask, "sarcasm_risk_heuristic"], final_df.loc[mask, "irony_prob"])
            spearman_r, _ = stats.spearmanr(final_df.loc[mask, "sarcasm_risk_heuristic"], final_df.loc[mask, "irony_prob"])
        else:
            pearson_r, spearman_r = 0.0, 0.0
    else:
        pearson_r, spearman_r = 0.0, 0.0
        
    prob_gt_05 = float((final_df["irony_prob"] > 0.5).mean())
    prob_gt_07 = float((final_df["irony_prob"] > 0.7).mean())
    
    high_mask = final_df["irony_prob"] > 0.5
    low_mask = final_df["irony_prob"] <= 0.5
    mean_score_high = float(final_df.loc[high_mask, "roberta_score"].mean()) if high_mask.sum() > 0 else 0.0
    mean_score_low = float(final_df.loc[low_mask, "roberta_score"].mean()) if low_mask.sum() > 0 else 0.0
    
    dist_by_sentiment = {}
    for lbl in final_df["roberta_label"].dropna().unique():
        sub = final_df[final_df["roberta_label"] == lbl]
        dist_by_sentiment[lbl] = float((sub["irony_prob"] > 0.5).mean()) if len(sub) > 0 else 0.0
        
    profile = {
        "pearson_heuristic_vs_irony": float(pearson_r),
        "spearman_heuristic_vs_irony": float(spearman_r),
        "share_gt_0.5": prob_gt_05,
        "share_gt_0.7": prob_gt_07,
        "mean_roberta_score_high_irony": mean_score_high,
        "mean_roberta_score_low_irony": mean_score_low,
        "share_high_irony_per_roberta_label": dist_by_sentiment
    }
    
    with open(evidence_dir / "irony_profile.json", "w") as f:
        json.dump(profile, f, indent=2)
        
    # T3.2 - Sample 15 human seeds
    # Stratify across stream_membership, roberta_label, irony band (high over-represented)
    # We will just pick manually to ensure coverage
    
    # 3 streams x 3 sentiments = 9 combinations. We can sample 1 or 2 from each.
    seed_df = pd.DataFrame()
    for stream in ["trump_only", "biden_only", "both"]:
        for sent in ["negative", "neutral", "positive"]:
            # try to get 1 high irony, 1 low irony if possible
            sub_high = final_df[(final_df["stream_membership"] == stream) & (final_df["roberta_label"] == sent) & (final_df["irony_prob"] > 0.5)]
            sub_low = final_df[(final_df["stream_membership"] == stream) & (final_df["roberta_label"] == sent) & (final_df["irony_prob"] <= 0.5)]
            
            if len(sub_high) > 0:
                seed_df = pd.concat([seed_df, sub_high.sample(n=1, random_state=42)])
            if len(sub_low) > 0:
                seed_df = pd.concat([seed_df, sub_low.sample(n=1, random_state=42)])
                
    # Sample down to exactly 15 rows if we got more
    seed_15 = seed_df.sample(n=15, random_state=42)
    
    out_records = []
    for _, row in seed_15.iterrows():
        out_records.append({
            "tweet_id": row["tweet_id"],
            "tweet_cleaned": row["tweet_cleaned"],
            "roberta_label": row["roberta_label"],
            "irony_prob": row["irony_prob"],
            "target_candidate": "",
            "stance": "",
            "expressed_sentiment": "",
            "intended_sentiment": "",
            "is_sarcastic": "",
            "annotator_note": "human_annotation_pending"
        })
        
    with open(anno_dir / "human_seed_15.jsonl", "w") as f:
        for rec in out_records:
            f.write(json.dumps(rec) + "\\n")
            
    print("Irony inference and sampling complete. T3.3/T3.4 blocked.")

if __name__ == "__main__":
    run_phase3_irony(PROJECT_ROOT)
