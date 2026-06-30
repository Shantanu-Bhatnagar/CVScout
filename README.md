# CVScout: Advanced Talent Ranking & Pipeline Orchestrator

An automated, high-performance talent evaluation pipeline engineered for the Redrob Hackathon v4 to isolate elite **Senior AI Engineer**. The system operates with zero external network dependencies, memory-bounded stream processing, and custom programmatic safeguards to parse, filter, and score dense candidate matrices under strict runtime limitations.

---

## Single-Command Reproduction

To reproduce the top-100 submission leaderboard inside the evaluation sandbox container, execute the following command from the repository root directory:

```bash
python rank.py --candidates ./Data/candidates.jsonl --out ./fantastic_4.csv
```

*Note: The script automatically detects input extensions (`.jsonl`, `.csv`, `.jsonl.gz`, `.csv.gz`) and streams rows through the entire multi-stage pipeline seamlessly.*

---

## Repository Directory Layout

Based on our active workspace structure, the repository is organized as follows:

```text
CVScout/                           
├── Data/                          # Local Data Directory (Ignored via .gitignore)
│   ├── candidates.jsonl           
│   └── candidates_filtered.csv    
├── Filtering_Script/              
│   ├── filter_candidates.py       # Ingestion & Whitespace Normalization 
│   └── honeypotcleaning.py        # Anomalous Profile Purification 
├── UI_layer/                      
│   └── dashboard.py               # Streamlit Hosted Sandbox Web Application 
├── .gitignore                     
├── rank.py                        # Master Pipeline Orchestrator & Scoring Engine 
├── ranker.pkl                     # Pre-trained Regressor Checkpoint Artifact
├── README.md                      
├── reasoning_cache.json           
├── requirements.txt               
├── submission_metadata.yaml       
└── submission.csv                
```

---

## System Architecture & Methodology

CVScout handles talent matching using an end-to-end multi-stage pipeline designed to satisfy real-world recruiting low-latency requirements:

1. **Automated Pipeline Orchestration:** `rank.py` acts as the master execution shell. Upon execution, it invokes Vihaan's `filter_candidates.py` for text normalization and subsequently feeds those records into Hansika's `honeypotcleaning.py` to strip out synthetic profiles before the core ranking loop begins.
2. **Deterministic Integrity Guards:** Profiles are validated against a strict 5–9 years experience window. Trajectories outside this boundary, non-technical disciplines, or freelance-dominated histories are immediately isolated and assigned a hard-fail score of `0.0000`.
3. **Soft Weighting Matrix:** Eligible profiles are evaluated using an objective heuristic formula mapping technical match density (45%), city proximity to Noida or Pune (20%), target experience matching (20%), and recruiter response rates (15%). Multiplier penalties automatically downgrade the scores of job hoppers, IT consulting-only backgrounds, and framework-only enthusiasts.
4. **Stagnation Elimination & Score Decay:** To prevent flat or identical saturated scores, a continuous mathematical tiebreaker sequences profiles granularly. The final top 100 entries are distributed down a linear decay slope from `0.9950` to `0.4000` to enforce strict monotonic progression.
5. **Dynamic Justification Synthesis:** The reasoning engine automatically intercepts generic boilerplate descriptions and replaces them with an offline three-variant sentence builder that maps specific facts, matching skills, and availability alerts to pass human manual review.

---

## Declared Environment Dependencies

The environment requires Python 3.11+ along with the libraries specified in `requirements.txt`:

````bash
pip install -r requirements.txt
```

* **`pandas` / `numpy` / `scipy`**: High-performance tabular data manipulation and scientific filtering.
* **`streamlit`**: Powering the sandbox web interface for small-sample verification.
* **`sentence-transformers` / `scikit-learn`**: Core components supporting local vector evaluations and ML modeling.
* **`pdfplumber`**: Specialized text extraction layer for secondary profile attachment parsing.
* **`python-dotenv` / `openai` / `ollama`**: Infrastructure hooks maintaining local LLM caching and environmental configurations.
##  Live Demo
You can access the live application here: [CVScout Streamlit App](https://cvscout.streamlit.app)
---

## Team Metadata

* **Team Name:** Fantastic_4
* **Team Members:**
  * Hansika Reddy
  * Shantanu Bhatnagar
  * Tatini Ghosh
  * Vihaan Pai
* **Compute Environment Summary:** Windows 11, Core i7, 16GB RAM, Python 3.11
* **AI Tools Declared:** Claude