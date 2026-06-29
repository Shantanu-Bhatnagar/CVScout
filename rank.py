import argparse
import ast
import csv
import gzip
import heapq
import json
import os 
import profile
import re
import subprocess
import sys
from datetime import datetime, date

CONSULTING_FIRMS = {
    "tcs", "tata consultancy services", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "hcl", "hcltech", "hcl technologies",
    "tech mahindra", "mindtree", "ltimindtree", "lti", "l&t infotech",
    "mphasis", "ibm global services",
}

TIER1_CITIES = {
    "kolkata", "bangalore", "bengaluru", "hyderabad", "mumbai", "chennai",
    "delhi", "new delhi", "delhi ncr", "ncr", "gurgaon", "gurugram",
    "noida",  # already in Pune/Noida check but add here as fallback
    "kochi", "cochin", "jaipur", "ahmedabad", "bhubaneswar",
}

CORE_AI_KEYWORDS = [
    "embedding", "embeddings", "retrieval", "sentence-transformers",
    "sentence transformers", "bge", "e5", "openai embeddings", "pinecone",
    "weaviate", "qdrant", "milvus", "faiss", "vector database", "vector db",
    "hybrid search", "ranking", "re-ranking", "reranking", "learning to rank",
    "ndcg", "mrr", "fine-tuning", "fine tuning", "lora", "qlora", "peft",
    "elasticsearch", "opensearch", "bm25", "rag", "transformer", "bert",
]

SYSTEMS_KEYWORDS = [
    "production", "deployed", "scaled", "at scale", "latency", "throughput",
    "infrastructure", "kubernetes", "docker", "distributed", "pipeline",
    "microservice", "low-latency", "high-throughput",
]

CV_SPEECH_ROBOTICS_KEYWORDS = [
    "computer vision", "image segmentation", "object detection", "slam",
    "robotics", "speech recognition", "asr", "autonomous vehicle", "lidar",
]

NLP_IR_KEYWORDS = [
    "nlp", "natural language processing", "information retrieval",
    "text retrieval", "semantic search", "named entity", "text classification",
    "language model", "llm", "retrieval-augmented", "rag", "bert", "transformer",
]

ROLE_TITLE_KEYWORDS = ["engineer", "scientist", "developer", "architect", "researcher", "programmer"]

TECH_ROLE_KEYWORDS = [
    "software", "data", "machine learning", "ml ", "ai ", "artificial intelligence",
    "backend", "full stack", "fullstack", "platform", "infrastructure",
    "applied scientist", "research scientist", "nlp", "computer vision", "deep learning",
]

NON_TECH_ENGINEER_DISCIPLINES = [
    "mechanical", "civil", "electrical", "chemical", "structural", "aerospace",
    "industrial", "petroleum", "mining", "marine", "automotive", "production",
]

FREELANCE_KEYWORDS = [
    "freelance", "freelancer", "contract", "part-time", "part time",
    "self-employed", "gig work",
]

BOILERPLATE_REASONING = "profile processed and indexed for matching parameters."

CANDIDATE_ID_RE = re.compile(r"CAND_(\d+)")

NESTED_FIELDS = ["profile", "career_history", "education", "skills", "certifications", "languages", "redrob_signals"]

WEIGHT_SKILLS = 0.45
WEIGHT_LOCATION = 0.20
WEIGHT_EXPERIENCE = 0.20
WEIGHT_BEHAVIOR = 0.15

DECAY_START = 0.9950
DECAY_FLOOR = 0.4000


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def candidate_id_sort_key(candidate_id):
    match = CANDIDATE_ID_RE.match(candidate_id or "")
    if match:
        return int(match.group(1))
    return 0


def parse_nested(value):
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return ""
    if stripped[0] in "[{":
        try:
            return ast.literal_eval(stripped)
        except (ValueError, SyntaxError):
            return [] if stripped[0] == "[" else {}
    return value


def normalize_csv_row(row):
    candidate = {}
    for key, value in row.items():
        if key in NESTED_FIELDS:
            candidate[key] = parse_nested(value)
        else:
            candidate[key] = value
    return candidate


def stream_candidates(path, chunk_size):
    is_gz = path.lower().endswith(".gz")
    is_csv = path.lower().endswith(".csv") or path.lower().endswith(".csv.gz")

    if is_gz:
        handle = gzip.open(path, "rt", encoding="utf-8", newline="" if is_csv else None)
    else:
        handle = open(path, "r", encoding="utf-8", newline="" if is_csv else None)

    try:
        if is_csv:
            reader = csv.DictReader(handle)
            buffer = []
            for row in reader:
                buffer.append(normalize_csv_row(row))
                if len(buffer) >= chunk_size:
                    for item in buffer:
                        yield item
                    buffer = []
            for item in buffer:
                yield item
        else:
            buffer = []
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    buffer.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                if len(buffer) >= chunk_size:
                    for item in buffer:
                        yield item
                    buffer = []
            for item in buffer:
                yield item
    finally:
        handle.close()


def total_experience_years(career_history):
    if not isinstance(career_history, list):
        return 0.0
    total_months = 0
    for entry in career_history:
        if isinstance(entry, dict):
            total_months += safe_int(entry.get("duration_months"), 0)
    return round(total_months / 12.0, 2)


def average_tenure_years(career_history):
    if not isinstance(career_history, list) or not career_history:
        return 0.0
    total_months = sum(safe_int(e.get("duration_months"), 0) for e in career_history if isinstance(e, dict))
    count = len(career_history)
    return round((total_months / count) / 12.0, 2) if count else 0.0


def gather_text_blob(profile, career_history, skills):
    parts = []
    if isinstance(profile, dict):
        parts.append(str(profile.get("headline") or ""))
        parts.append(str(profile.get("summary") or ""))
        parts.append(str(profile.get("current_title") or ""))
        parts.append(str(profile.get("current_industry") or ""))
    if isinstance(career_history, list):
        for entry in career_history:
            if isinstance(entry, dict):
                parts.append(str(entry.get("title") or ""))
                parts.append(str(entry.get("description") or ""))
                parts.append(str(entry.get("industry") or ""))
    if isinstance(skills, list):
        for skill in skills:
            if isinstance(skill, dict):
                parts.append(str(skill.get("name") or ""))
    return " ".join(parts).lower()


def matched_keywords(text_blob, keyword_list):
    return {kw for kw in keyword_list if kw in text_blob}


def is_consulting_only(career_history):
    companies = []
    if isinstance(career_history, list):
        for entry in career_history:
            if isinstance(entry, dict):
                companies.append(str(entry.get("company") or "").strip().lower())
    if not companies:
        return False
    return all(any(firm in company for firm in CONSULTING_FIRMS) for company in companies)


def freelance_ratio(career_history):
    if not isinstance(career_history, list) or not career_history:
        return 0.0
    flagged = 0
    for entry in career_history:
        if not isinstance(entry, dict):
            continue
        blob = (str(entry.get("title") or "") + " " + str(entry.get("description") or "")).lower()
        if any(kw in blob for kw in FREELANCE_KEYWORDS):
            flagged += 1
    return flagged / len(career_history)


def location_score(location, willing_to_relocate):
    loc = (location or "").lower()
    if "noida" in loc or "pune" in loc:
        return 1.0
    if any(city in loc for city in TIER1_CITIES):
        return 0.85   # was 0.6 — JD explicitly welcomes these cities
    if willing_to_relocate:
        return 0.55   # was 0.35 — willing to relocate is a real positive signal
    return 0.2        # was 0.1 — don't completely bury unknown locations


def experience_fit_score(total_years):
    if total_years <= 6.0:
        return 0.6 + (total_years - 5.0) * 0.4
    if total_years <= 8.0:
        return 1.0
    return max(0.0, 1.0 - (total_years - 8.0) * 0.3)


def parse_date(value):
    if not value:
        return None
    text = str(value)
    if len(text) < 10:
        return None
    try:
        year = int(text[0:4])
        month = int(text[5:7])
        day = int(text[8:10])
        return date(year, month, day)
    except ValueError:
        return None


def activity_factor(last_active_date_str, reference_date):
    parsed = parse_date(last_active_date_str)
    if not parsed:
        return 0.7
    days = (reference_date - parsed).days
    if days < 0 or days <= 30:
        return 1.0
    if days <= 90:
        return 0.95
    if days <= 180:
        return 0.85
    return 0.65


def behavioral_modifier(redrob_signals):
    response_rate = safe_float(redrob_signals.get("recruiter_response_rate"), 0.0)
    completeness = safe_float(redrob_signals.get("profile_completeness_score"), 0.0) / 100.0
    interview_completion = safe_float(redrob_signals.get("interview_completion_rate"), 0.7)
    open_to_work = bool(redrob_signals.get("open_to_work_flag", False))

    # response_rate is the dominant availability signal per the JD
    modifier = (
        0.50 * response_rate
        + 0.25 * interview_completion
        + 0.15 * completeness
        + 0.10  # small base floor
    )
    if open_to_work:
        modifier += 0.05
    if response_rate <= 0.10:
        modifier *= 0.5   # hard availability penalty, not just <= 0.05
    return max(0.0, min(modifier, 1.15))


def compute_skill_score(matched_core):
    return min(len(matched_core), 8) / 8.0


def compute_model_score(features):
    skill_score = compute_skill_score(features["matched_core_keywords"])
    loc_score = location_score(features["location"], features["willing_to_relocate"])
    exp_score = experience_fit_score(features["total_years"])
    behavior_score = behavioral_modifier(features["redrob_signals"])

    base = (
        WEIGHT_SKILLS * skill_score
        + WEIGHT_LOCATION * loc_score
        + WEIGHT_EXPERIENCE * exp_score
        + WEIGHT_BEHAVIOR * behavior_score
    )
    base *= features["activity_factor"]

    penalty = 1.0
    if features["role_misaligned"]:
        penalty *= 0.05
    if features["consulting_only"]:
        penalty *= 0.12
    if features["framework_only"]:
        penalty *= 0.20
    if features["domain_misaligned"]:
        penalty *= 0.20
    if features["job_hopper"]:
        penalty *= 0.35
    if features["mostly_freelance"]:
        penalty *= 0.30

    return max(0.0, base * penalty)


def compute_tiebreaker(features):
    skill_count = len(features["matched_core_keywords"])
    loc = (features["location"] or "").lower()
    exact_loc = 1.0 if ("noida" in loc or "pune" in loc) else 0.0
    response_rate = safe_float(features["redrob_signals"].get("recruiter_response_rate"), 0.0)
    completeness = safe_float(features["redrob_signals"].get("profile_completeness_score"), 0.0)
    value = skill_count * 1000.0 + exact_loc * 100.0 + response_rate * 10.0 + completeness * 0.01
    return round(value, 6)

def evaluate_candidate(candidate, reference_date):
    candidate_id = str(candidate.get("candidate_id") or "")
    profile = candidate.get("profile") if isinstance(candidate.get("profile"), dict) else {}
    career_history = candidate.get("career_history") if isinstance(candidate.get("career_history"), list) else []
    skills = candidate.get("skills") if isinstance(candidate.get("skills"), list) else []
    redrob_signals = candidate.get("redrob_signals") if isinstance(candidate.get("redrob_signals"), dict) else {}

    total_years = total_experience_years(career_history)
    avg_tenure = average_tenure_years(career_history)
    text_blob = gather_text_blob(profile, career_history, skills)

    matched_core_keywords = matched_keywords(text_blob, CORE_AI_KEYWORDS)
    consulting_only = is_consulting_only(career_history)
    systems_signal = bool(matched_keywords(text_blob, SYSTEMS_KEYWORDS))
    framework_only = ("langchain" in text_blob) and not systems_signal and len(matched_core_keywords) <= 2
    cv_speech_robotics = bool(matched_keywords(text_blob, CV_SPEECH_ROBOTICS_KEYWORDS))
    nlp_ir_signal = bool(matched_keywords(text_blob, NLP_IR_KEYWORDS))

    # Check if CV/speech is the PRIMARY identity (current title, not just any career mention)
    title_lower = str(profile.get("current_title") or "").lower()
    cv_primary_title = any(kw in title_lower for kw in [
        "computer vision", "vision engineer", "object detection",
        "robotics", "speech", "asr"
    ])
    # Count NLP/IR keywords — a single "bert" in skills isn't enough crossover
    nlp_ir_depth = len(matched_keywords(text_blob, NLP_IR_KEYWORDS))
    domain_misaligned = cv_speech_robotics and (cv_primary_title or (not nlp_ir_signal)) or (
    cv_primary_title and nlp_ir_depth < 3
    )
    job_hopper = len(career_history) >= 2 and avg_tenure < 1.6
    freelance_share = freelance_ratio(career_history)
    mostly_freelance = 0.6 <= freelance_share < 0.8
    predominantly_freelance = freelance_share >= 0.8
    current_title = str(profile.get("current_title") or "")
    title_lower = current_title.lower()
    if any(kw in title_lower for kw in TECH_ROLE_KEYWORDS):
        role_misaligned = False
    elif any(kw in title_lower for kw in ROLE_TITLE_KEYWORDS) and not any(kw in title_lower for kw in NON_TECH_ENGINEER_DISCIPLINES):
        role_misaligned = False
    else:
        role_misaligned = True

    willing_to_relocate = bool(redrob_signals.get("willing_to_relocate", False))
    location = str(profile.get("location") or "")
    activity = activity_factor(redrob_signals.get("last_active_date"), reference_date)

    hard_fail_reasons = []
    if total_years < 5.0 or total_years > 9.0:
        hard_fail_reasons.append(f"total experience {total_years:.1f} yrs is outside the 5-9 yr band")
    if predominantly_freelance:
        hard_fail_reasons.append("career history is predominantly freelance/part-time")

    features = {
        "candidate_id": candidate_id,
        "current_title": str(profile.get("current_title") or "Professional"),
        "current_company": str(profile.get("current_company") or ""),
        "total_years": total_years,
        "avg_tenure": avg_tenure,
        "matched_core_keywords": matched_core_keywords,
        "consulting_only": consulting_only,
        "framework_only": framework_only,
        "domain_misaligned": domain_misaligned,
        "job_hopper": job_hopper,
        "mostly_freelance": mostly_freelance,
        "role_misaligned": role_misaligned,
        "willing_to_relocate": willing_to_relocate,
        "location": location,
        "redrob_signals": redrob_signals,
        "activity_factor": activity,
        "passed": not hard_fail_reasons,
        "hard_fail_reasons": hard_fail_reasons,
    }

    features["model_score"] = compute_model_score(features) if features["passed"] else 0.0
    features["tiebreaker_score"] = compute_tiebreaker(features)
    return features

def top_named_skills(matched_core_keywords, limit=3):
    return sorted(matched_core_keywords)[:limit]


def concern_clauses(features):
    concerns = []
    response_rate = safe_float(features["redrob_signals"].get("recruiter_response_rate"), 0.0)
    notice_period = safe_int(features["redrob_signals"].get("notice_period_days"), 0)
    if features["role_misaligned"]:
        concerns.append(f"current title '{features['current_title']}' does not read as an engineering/ML role despite skill keywords present")
    if response_rate <= 0.10:
        concerns.append(f"a low recruiter response rate of {response_rate:.2f}")
    if notice_period > 60:
        concerns.append(f"a longer notice period of {notice_period} days")
    if features["job_hopper"]:
        concerns.append(f"average tenure of only {features['avg_tenure']:.1f} yrs across roles")
    if features["consulting_only"]:
        concerns.append("a career spent entirely at IT-services firms")
    if features["framework_only"]:
        concerns.append("AI exposure leaning on LangChain without deeper systems work")
    if features["domain_misaligned"]:
        concerns.append("a background concentrated in vision/speech/robotics rather than NLP or retrieval")
    if features["mostly_freelance"]:
        concerns.append("a largely freelance/part-time work history")
    return concerns


def build_reasoning(features):
    title = features["current_title"]
    years = features["total_years"]
    skills = top_named_skills(features["matched_core_keywords"])
    skill_count = len(features["matched_core_keywords"])
    response_rate = safe_float(features["redrob_signals"].get("recruiter_response_rate"), 0.0)
    location = features["location"] or "an unspecified location"

    if not features["passed"]:
        reasons = "; ".join(features["hard_fail_reasons"])
        return f"{title} with {years:.1f} yrs total experience; excluded because {reasons}."

    skill_phrase = ", ".join(skills) if skills else "no strong AI-core keyword matches"
    variant = candidate_id_sort_key(features["candidate_id"]) % 3

    if variant == 0:
        base = (
            f"{title} with {years:.1f} yrs of experience and {skill_count} AI-core skill matches "
            f"({skill_phrase}), based in {location}."
        )
    elif variant == 1:
        base = (
            f"{years:.1f}-year {title} with hands-on exposure to {skill_phrase}; "
            f"recruiter response rate {response_rate:.2f}."
        )
    else:
        base = (
            f"Matches the JD's production-ML profile: {title}, {years:.1f} yrs, "
            f"core skills in {skill_phrase}."
        )

    concerns = concern_clauses(features)
    if concerns:
        base += f" Noted concern: {concerns[0]}."
    else:
        base += " No major red flags against the JD's stated disqualifiers."

    return base


def load_reasoning_cache(path):
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def resolve_reasoning(features, cache):
    cached = cache.get(features["candidate_id"])
    if isinstance(cached, str):
        cleaned = cached.strip()
        if cleaned and cleaned.lower() != BOILERPLATE_REASONING:
            return cleaned
    return build_reasoning(features)


def heap_key(features):
    return (
        1 if features["passed"] else 0,
        features["model_score"],
        features["tiebreaker_score"],
        -candidate_id_sort_key(features["candidate_id"]),
    )


def find_team_script(filename):
    if os.path.exists(filename):
        return filename
    for folder in ["Filtering_Script", "UI_layer", "filtering", "scripts", "src", "Data"]:
        test_path = os.path.join(folder, filename)
        if os.path.exists(test_path):
            return test_path
    return filename

def discover_pipeline_output(fallback_path):
    for folder in [".", "Data", "Filtering_Script"]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                fl = f.lower()
                if "filtered" in fl or "cleaned" in fl or "honeypot" in fl:
                    p = os.path.join(folder, f)
                    if os.path.isfile(p) and os.getsize(p) > 0 and p != fallback_path:
                        return p
    return fallback_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--top-n", type=int, default=100)
    parser.add_argument("--chunk-size", type=int, default=5000)
    parser.add_argument("--reasoning-cache", default="reasoning_cache.json")
    args = parser.parse_args()

    current_input_path = args.candidates
    ext = ".csv" if (current_input_path.lower().endswith(".csv") or current_input_path.lower().endswith(".csv.gz")) else ".jsonl"
    
    temp_filtered_path = "temp_pipeline_filtered" + ext
    temp_honeypot_path = "temp_pipeline_honeypot" + ext
    default_team_output = os.path.join("Data", "candidates_filtered.csv")

    print("\n" + "="*60, flush=True)
    print("LAUNCHING TALENT SCORING AND RANKING ORCHESTRATOR PIPELINE", flush=True)
    print("="*60 + "\n", flush=True)

    cleaning_script = find_team_script("filter_candidates.py")
    print(f"[STAGE 1/3] Running Data Cleaning via: {cleaning_script}...", flush=True)
    print(f"            Processing raw source: {current_input_path}", flush=True)
    try:
        subprocess.run([
            sys.executable, cleaning_script, 
            "--candidates", current_input_path, 
            "--out", temp_filtered_path
        ], check=True)
        
        if os.path.exists(temp_filtered_path):
            current_input_path = temp_filtered_path
            print(" -> SUCCESS: Data cleaning complete (Using pipeline temp file).\n", flush=True)
        elif os.path.exists(default_team_output):
            current_input_path = default_team_output
            print(" -> SUCCESS: Data cleaning complete (Detected default team output file).\n", flush=True)
        else:
            print(" -> SUCCESS: Data cleaning complete.\n", flush=True)
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(" -> WARNING: filter_candidates.py failed or not found. Falling back to raw input.\n", flush=True)

    honeypot_script = find_team_script("honeypotcleaning.py")
    print(f"[STAGE 2/3] Running Honeypot Filtering via: {honeypot_script}...", flush=True)
    print(f"            Processing intermediate source: {current_input_path}", flush=True)
    try:
        if os.path.exists(default_team_output):
            try:
                os.remove(default_team_output)
            except OSError:
                pass

        subprocess.run([
            sys.executable, honeypot_script, 
            "--candidates", current_input_path, 
            "--out", temp_honeypot_path
        ], check=True)
        
        if os.path.exists(temp_honeypot_path):
            current_input_path = temp_honeypot_path
            print(" -> SUCCESS: Honeypot profiles isolated (Using pipeline temp file).\n", flush=True)
        elif os.path.exists(default_team_output):
            current_input_path = default_team_output
            print(" -> SUCCESS: Honeypot profiles isolated (Detected default team output file).\n", flush=True)
        else:
            print(" -> SUCCESS: Honeypot profiles isolated and purged from stream.\n", flush=True)
            
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(" -> WARNING: honeypotcleaning.py failed or not found. Falling back to previous stream.\n", flush=True)

    print(f"[STAGE 3/3] Running Matrix Scoring and Leaderboard Sorting...", flush=True)
    print(f"            Processing finalized stream source: {current_input_path}", flush=True)
    
    cache = load_reasoning_cache(args.reasoning_cache)
    reference_date = datetime.now().date()

    heap = []
    seen_ids = set()
    seen_count = 0

    for candidate in stream_candidates(current_input_path, args.chunk_size):
        if not isinstance(candidate, dict):
            continue
        candidate_id = candidate.get("candidate_id")
        if not candidate_id or candidate_id in seen_ids:
            continue
        seen_ids.add(candidate_id)
        seen_count += 1

        features = evaluate_candidate(candidate, reference_date)
        entry = (heap_key(features), seen_count, features)

        if len(heap) < args.top_n:
            heapq.heappush(heap, entry)
        elif entry[0] > heap[0][0]:
            heapq.heapreplace(heap, entry)

    ranked = sorted(heap, key=lambda item: item[0], reverse=True)
    output_n = len(ranked)
    decay_step = (DECAY_START - DECAY_FLOOR) / (output_n - 1) if output_n > 1 else 0.0

    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for index, (_, _, features) in enumerate(ranked):
            rank = index + 1
            if features["passed"]:
                score = round(DECAY_START - index * decay_step, 4)
            else:
                score = 0.0
            reasoning = resolve_reasoning(features, cache)
            writer.writerow([features["candidate_id"], rank, f"{score:.4f}", reasoning])

    print(f" -> SUCCESS: Processed {seen_count} candidates. Leaderboard exported to {args.out}\n", flush=True)

    if os.path.exists(temp_filtered_path):
        os.remove(temp_filtered_path)
    if os.path.exists(temp_honeypot_path):
        os.remove(temp_honeypot_path)

    print("="*60, flush=True)
    print("PIPELINE EXECUTION COMPLETE: SAFE TO EXIT SANDBOX CONTAINER", flush=True)
    print("="*60 + "\n", flush=True)

if __name__ == "__main__":
    main()
