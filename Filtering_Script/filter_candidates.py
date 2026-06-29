import json
from datetime import datetime, date


INPUT_FILE  = "candidates_cleaned__20.jsonl"
OUTPUT_FILE = "candidates_filtered.jsonl"
REJECTED_FILE = "candidates_rejected.jsonl"

CONSULTING_FIRMS = [
    "tcs", "tata consultancy services", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "hcl", "tech mahindra", "mphasis",
    "hexaware", "ltimindtree", "l&t infotech", "coforge", "niit technologies"
]

CV_SPEECH_SKILLS = [
    "computer vision", "object detection", "image classification", "image segmentation",
    "speech recognition", "speech synthesis", "tts", "asr", "robotics", "ros",
    "autonomous vehicles", "lidar", "slam"
]

NLP_IR_SKILLS = [
    "nlp", "natural language", "information retrieval", "text classification",
    "embedding", "vector search", "retrieval", "ranking", "search", "bert",
    "transformer", "llm", "rag", "semantic search", "question answering",
    "named entity", "sentiment", "text mining"
]

def months_since(date_str):
    """How many months ago was this date?"""
    if not date_str:
        return None
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        today = date.today()
        return (today.year - d.year) * 12 + (today.month - d.month)
    except:
        return None

def get_all_skill_names(record):
    return [s.get("name", "").lower() for s in record.get("skills", [])]

def get_all_companies(career_history):
    return [(j.get("company") or "").lower().strip() for j in career_history]

def get_all_titles(career_history):
    return [(j.get("title") or "").lower().strip() for j in career_history]

def get_all_descriptions(career_history):
    return " ".join((j.get("description") or "").lower() for j in career_history)

def total_experience_years(career_history):
    months = sum(j.get("duration_months") or 0 for j in career_history)
    return months / 12



def check_experience_range(record):
    """
    JD: "5–9 years required" but flexible (4–10 accepted if other signals strong).
    Hard disqualify below 4 or above 10.
    """
    yrs = total_experience_years(record.get("career_history", []))
    if yrs < 4:
        return True, f"Too little experience: {yrs:.1f} yrs (need 5–9)"
    if yrs > 10:
        return True, f"Too much experience: {yrs:.1f} yrs (likely overqualified or title-chaser)"
    return False, ""

def check_not_open_to_work(record):
    """
    Signals doc: open_to_work_flag — have they marked themselves available.
    If False, not in job market.
    """
    if not record["redrob_signals"].get("open_to_work_flag", True):
        return True, "Not open to work (open_to_work_flag = false)"
    return False, ""

def check_inactivity(record):
    """
    JD + Signals doc: "hasn't logged in for 6 months = not actually available"
    last_active_date > 6 months ago = disqualify.
    """
    months = months_since(record["redrob_signals"].get("last_active_date"))
    if months is not None and months > 6:
        return True, f"Inactive for {months} months (last_active_date)"
    return False, ""

def check_recruiter_response_rate(record):
    """
    JD: "5% recruiter response rate = not actually available"
    Signals doc: recruiter_response_rate 0.0–1.0
    Disqualify below 10%.
    """
    rate = record["redrob_signals"].get("recruiter_response_rate")
    if rate is not None and rate < 0.10:
        return True, f"Recruiter response rate too low: {rate:.0%}"
    return False, ""

def check_notice_period(record):
    """
    JD: "love sub-30 days, can buy out 30 days, 30+ still in scope but bar higher"
    Signals doc: notice_period_days 0–180
    Hard disqualify above 90 days.
    """
    notice = record["redrob_signals"].get("notice_period_days")
    if notice is not None and notice > 90:
        return True, f"Notice period too long: {notice} days"
    return False, ""

def check_consulting_only(record):
    """
    JD: "People who have ONLY worked at consulting firms (TCS, Infosys, Wipro,
    Accenture, Cognizant, Capgemini) — disqualified. If currently at one but has
    prior product-company experience, that's fine."
    """
    career = record.get("career_history", [])
    if not career:
        return False, ""
    companies = get_all_companies(career)
    for company in companies:
        is_consulting = any(firm in company for firm in CONSULTING_FIRMS)
        if not is_consulting:
            return False, ""  
    return True, "Entire career at consulting firms only (TCS/Infosys/Wipro etc.)"

def check_pure_research(record):
    """
    JD: "career in pure research environments (academic labs, research-only roles)
    without any production deployment — will not move forward"
    Check if ALL jobs are research/academic with no production signal.
    """
    career = record.get("career_history", [])
    if not career:
        return False, ""

    research_keywords = ["research", "academic", "university", "lab", "professor", "phd", "scientist"]
    production_keywords = ["engineer", "developer", "sde", "swe", "architect", "lead", "manager",
                           "analyst", "product", "backend", "frontend", "fullstack", "data engineer",
                           "ml engineer", "ai engineer", "platform"]

    all_research = True
    for job in career:
        title = (job.get("title") or "").lower()
        industry = (job.get("industry") or "").lower()
        has_research = any(k in title or k in industry for k in research_keywords)
        has_production = any(k in title for k in production_keywords)
        if has_production or (not has_research):
            all_research = False
            break

    if all_research:
        return True, "Pure research/academic career — no production deployment"
    return False, ""

def check_job_hopping(record):
    """
    JD: "Title-chasers optimizing for Senior→Staff→Principal by switching every 1.5 years"
    If candidate has 3+ jobs AND average tenure < 18 months → disqualify.
    """
    career = record.get("career_history", [])
    tenures = [j.get("duration_months", 0) for j in career if j.get("duration_months")]
    if len(tenures) >= 3:
        avg_tenure = sum(tenures) / len(tenures)
        if avg_tenure < 18:
            return True, f"Job hopper: avg tenure {avg_tenure:.0f} months across {len(tenures)} jobs"
    return False, ""

def check_cv_speech_only(record):
    """
    JD: "People whose primary expertise is computer vision, speech, or robotics
    WITHOUT significant NLP/IR exposure — disqualified"
    """
    skills = get_all_skill_names(record)
    desc = get_all_descriptions(record.get("career_history", []))

    has_cv_speech = any(any(k in s for k in CV_SPEECH_SKILLS) for s in skills)
    if not has_cv_speech:
        has_cv_speech = any(k in desc for k in CV_SPEECH_SKILLS)
    if not has_cv_speech:
        return False, ""  

    has_nlp_ir = any(any(k in s for k in NLP_IR_SKILLS) for s in skills)
    if not has_nlp_ir:
        has_nlp_ir = any(k in desc for k in NLP_IR_SKILLS)

    if not has_nlp_ir:
        return True, "Primary expertise is CV/speech/robotics with no NLP/IR exposure"
    return False, ""

def check_wrapper_only_ai(record):
    """
    JD: "AI experience consists primarily of recent (<12 months) LangChain/OpenAI
    projects — will not move forward unless substantial pre-LLM ML experience"
    Disqualify if:
      - Only AI skills are LangChain/OpenAI wrappers with <12 months duration
      - AND no real ML skills (embeddings, retrieval, ranking, transformers etc.)
    """
    skills = record.get("skills", [])
    wrapper_skills = [s for s in skills if any(
        x in s.get("name", "").lower() for x in ["langchain", "openai api", "chatgpt api", "gpt wrapper"]
    )]
    if not wrapper_skills:
        return False, ""

    all_wrappers_recent = all(s.get("duration_months", 99) < 12 for s in wrapper_skills)
    if not all_wrappers_recent:
        return False, "" 
  
    real_ml = [s for s in skills if any(
        x in s.get("name", "").lower()
        for x in ["embedding", "retrieval", "vector", "ranking", "nlp", "transformer",
                  "bert", "fine-tun", "rag", "semantic", "recommendation", "xgboost",
                  "pytorch", "tensorflow", "sklearn", "scikit"]
    )]
    if not real_ml:
        return True, "AI experience is only recent LangChain/OpenAI wrappers (<12mo), no real ML"
    return False, ""

def check_location(record):
    """
    JD: "Outside India — case-by-case, but no visa sponsorship"
    Disqualify if country is not India AND not willing to relocate.
    """
    profile = record.get("profile", {})
    country = (profile.get("country") or "").lower().strip()
    if country in ("india", "in", ""):
        return False, ""
    willing = record["redrob_signals"].get("willing_to_relocate", True)
    if not willing:
        return True, f"Outside India ({profile.get('country')}) and not willing to relocate"
    return False, ""

def check_interview_completion(record):
    """
    Signals doc: interview_completion_rate 0.0–1.0
    Candidates who ghost interviews are not actually hirable.
    Disqualify below 30%.
    """
    icr = record["redrob_signals"].get("interview_completion_rate")
    if icr is not None and icr < 0.30:
        return True, f"Interview completion rate too low: {icr:.0%} (ghosting signal)"
    return False, ""

def check_profile_completeness(record):
    """
    Signals doc: profile_completeness_score 0–100
    Very incomplete profiles = not serious about job search.
    Disqualify below 40.
    """
    score = record["redrob_signals"].get("profile_completeness_score")
    if score is not None and score < 40:
        return True, f"Profile too incomplete: {score}/100"
    return False, ""

def check_verified_contact(record):
    """
    Signals doc: verified_email and verified_phone
    If BOTH are unverified, candidate is unreachable — disqualify.
    """
    email_ok = record["redrob_signals"].get("verified_email", True)
    phone_ok = record["redrob_signals"].get("verified_phone", True)
    if not email_ok and not phone_ok:
        return True, "Neither email nor phone is verified — unreachable"
    return False, ""

ALL_CHECKS = [
    check_experience_range,
    check_not_open_to_work,
    check_inactivity,
    check_recruiter_response_rate,
    check_notice_period,
    check_consulting_only,
    check_pure_research,
    check_job_hopping,
    check_cv_speech_only,
    check_wrapper_only_ai,
    check_location,
    check_interview_completion,
    check_profile_completeness,
    check_verified_contact,
]

def should_keep(record):
    for check in ALL_CHECKS:
        failed, reason = check(record)
        if failed:
            return False, reason
    return True, "PASS"

kept = 0
rejected = 0
rejection_reasons = {}

with open(INPUT_FILE, "r") as fin, \
     open(OUTPUT_FILE, "w") as fout, \
     open(REJECTED_FILE, "w") as rout:

    for line in fin:
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        keep, reason = should_keep(record)

        if keep:
            fout.write(json.dumps(record) + "\n")
            kept += 1
        else:
            record["_filter_reason"] = reason
            rout.write(json.dumps(record) + "\n")
            rejected += 1
            # group reason by type (before the colon)
            key = reason.split(":")[0].split("(")[0].strip()
            rejection_reasons[key] = rejection_reasons.get(key, 0) + 1

total = kept + rejected
print(f"\n{'='*50}")
print(f"  FILTER RESULTS")
print(f"{'='*50}")
print(f"  Total processed : {total:,}")
print(f"  ✅ Kept         : {kept:,}")
print(f"  ❌ Rejected     : {rejected:,}")
print(f"\n  Rejection breakdown:")
for reason, count in sorted(rejection_reasons.items(), key=lambda x: -x[1]):
    pct = count / total * 100
    print(f"    {reason:<45} {count:>6,}  ({pct:.1f}%)")
print(f"\n  Output  → {OUTPUT_FILE}")
print(f"  Rejects → {REJECTED_FILE}")
print(f"{'='*50}\n")
