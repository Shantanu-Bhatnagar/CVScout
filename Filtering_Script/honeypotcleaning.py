import csv
import json
from datetime import datetime, date


import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--candidates", default="candidates_cleaned__20.jsonl")
parser.add_argument("--out", default="temp_pipeline_honeypot.jsonl")
args = parser.parse_args()

INPUT_FILE = args.candidates
OUTPUT_FILE = args.out
REJECTED_FILE = "candidates_rejected.jsonl"
OUTPUT_CSV  = "candidates_filtered.csv"

# Current timeline context baseline
BASELINE_DATE = date(2026, 6, 28)

CONSULTING_FIRMS = [
    "tcs", "tata consultancy", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "hcl", "tech mahindra", "mphasis",
    "hexaware", "ltimindtree"
]

def clean_text(text):
    return " ".join(str(text).lower().split())

def is_eligible(candidate):
    signals = candidate.get("redrob_signals", {})
    full_dump = clean_text(json.dumps(candidate))
    
   
   
    yrs = candidate.get("experience_years") or candidate.get("total_experience")
    if yrs is None:
        months = sum(j.get("duration_months") or 0 for j in candidate.get("career_history", []))
        yrs = months / 12
        
    if yrs < 4.0: 
        return False, "Too little experience (< 4 years)"

    commit_gap = candidate.get("months since last production commit") or candidate.get("months_since_last_production_commit")
    if commit_gap is not None and commit_gap > 18:
        return False, "Out of production coding for 18+ months"

  
    last_active_str = signals.get("last_active_date")
    if last_active_str:
        try:
            d = datetime.strptime(last_active_str[:10], "%Y-%m-%d").date()
            months_inactive = (BASELINE_DATE.year - d.year) * 12 + (BASELINE_DATE.month - d.month)
            if months_inactive > 12:
                return False, "Inactive on platform over 12 months"
        except:
            pass

    response_rate = signals.get("recruiter_response_rate")
    if response_rate is not None and response_rate <= 0.05:
        return False, "Ghoster signal (Recruiter response rate <= 5%)"


    if "academic lapse" in full_dump or "gap year due to backlog" in full_dump:
        return False, "Academic lapse / baseline structural break"

    career = candidate.get("career_history", [])
    if career:
        all_consulting = True
        for job in career:
            comp = clean_text(job.get("company", ""))
            if not any(firm in comp for firm in CONSULTING_FIRMS):
                all_consulting = False
                break
        if all_consulting:
            return False, "Entire career history tied to consulting firms only"

    if "research scientist" in full_dump or "postdoc" in full_dump:
        production_signals = ["production", "deployed", "shipping", "scaled", "kubernetes", "aws", "ci/cd", "pipeline"]
        if not any(x in full_dump for x in production_signals):
            return False, "Pure research role without validation of production engineering"


    if "langchain" in full_dump and "openai" in full_dump:
        depth_signals = ["vector", "embedding", "retrieval", "fine-tuning", "rerank", "hybrid search", "ndcg", "mrr", "bge", "e5"]
        if not any(x in full_dump for x in depth_signals):
            return False, "LangChain tutorial/wrapper profile without system depth"


    has_ml_systems = any(x in full_dump for x in [
        "embedding", "retrieval", "ranking", "vector", "search", 
        "fine-tuning", "llm", "rag", "transformers", "xgboost"
    ])
    if not has_ml_systems:
        return False, "Lacks fundamental ML systems / Information Retrieval architecture"

    return True, "PASS"

def flatten_for_csv(record, reason="PASS"):
    flat = {"filter_status": reason}
    for k, v in record.items():
        if k == "redrob_signals" and isinstance(v, dict):
            for sk, sv in v.items():
                if sk != "skill_assessment_scores":
                    flat[f"signal_{sk}"] = sv
        elif isinstance(v, (list, dict)):
            flat[k] = json.dumps(v, ensure_ascii=False)
        else:
            flat[k] = v
    return flat


kept_records = []
rejection_reasons = {}
total, kept, rejected = 0, 0, 0

with open(INPUT_FILE, "r", encoding="utf-8") as fin, \
     open(OUTPUT_FILE, "w", encoding="utf-8") as fout, \
     open(REJECTED_FILE, "w", encoding="utf-8") as rout:

    for line in fin:
        if not line.strip():
            continue
        total += 1
        record = json.loads(line)
        keep, reason = is_eligible(record)
        
        if keep:
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            kept_records.append(flatten_for_csv(record, "PASS"))
            kept += 1
        else:
            record["_filter_reason"] = reason
            rout.write(json.dumps(record, ensure_ascii=False) + "\n")
            rejected += 1
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

if kept_records:
    headers = sorted(list({k for r in kept_records for k in r.keys()}))
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fcsv:
        writer = csv.DictWriter(fcsv, fieldnames=headers)
        writer.writeheader()
        writer.writerows(kept_records)


print("PIPELINE EXECUTION SUMMARY")
print(f"Total Evaluated Records : {total:,}")
print(f"Accepted Matches        : {kept:,}")
print(f"Rejected Entries        : {rejected:,}")
print("")
print("Funnel Drop Distribution:")

for reason, count in sorted(rejection_reasons.items(), key=lambda x: -x[1]):
    safe_reason = reason.encode('ascii', 'ignore').decode('ascii').strip()
    print(f"  -> {safe_reason:<60} : {count:>6,} ({count/total*100:.1f}%)")
    
print("")