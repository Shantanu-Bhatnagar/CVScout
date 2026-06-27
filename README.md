# FitChex: Dual-Stage Machine Learning Candidate Ranking Engine

FitChex is a high-performance, memory-bounded evaluation pipeline designed to ingest large-scale candidate datasets, filter out structural disqualifiers, and rank profiles using a locally trained gradient-boosted decision tree model.

The system operates entirely offline and executes within strict CPU performance limits. It evaluates candidate records by combining automated business-rule filtering, numerical feature extraction (experience gaps, hard skills matching, and behavioral metrics), and pre-computed language model justifications.

---

## Technical Architecture

The project utilizes a decoupled two-stage architecture to maximize evaluation accuracy while respecting sandboxed platform limitations:

1. **Offline Pre-computation Layer:** Runs locally to evaluate historical datasets. A large language model analyzes raw profile text to generate qualitative hiring justifications, which are saved in a key-value lookup file (`reasoning_cache.json`). Simultaneously, a LightGBM regressor model is trained on structural and behavioral features to learn optimal candidate alignment, exporting a lightweight serialized brain (`ranker.pkl`).
2. **Production Sandbox Runtime (`rank.py`):** The script executed by the evaluation platform. It streams incoming candidates line-by-line to guarantee a flat memory footprint, enforces automated rule-based filters to eliminate honeypots, processes numerical features, computes suitability scores using the LightGBM model, and executes a deterministic tie-breaking sort.

---

## Tech Stack

* **Core Runtime:** Python 3.8+
* **Machine Learning & Inference:** LightGBM, Scikit-learn, Pickle
* **Data Processing & Array Math:** NumPy, Pandas
* **Interface & Visualization:** Streamlit

---

## Directory Layout

```text
Ai-Candidate-Ranker/
│
├── data/
│   ├── raw_resumes/            # Source location for candidate datasets
│   └── job_description.txt     # Target role requirements in plain text
│
├── data_layer/
│   └── filter_candidates.py    # Hard filter, honeypot detection, and stream validation
│
├── ai_engine/
│   ├── rank.py                 # Sandbox execution engine loaded with the trained model
│   ├── ranker.pkl              # Serialized LightGBM scoring model
│   └── reasoning_cache.json    # Pre-computed LLM hiring justifications lookup table
│
├── ui_layer/
│   └── app.py                  # Streamlit visual interface for recruiter interaction
│
├── requirements.txt            # System dependencies and versions
└── README.md                   # System documentation

```

---

## Installation and Setup

Install the required data engineering and machine learning dependencies inside your Python environment:

```bash
pip install -r requirements.txt

```

---

## Usage and Implementation

The production runtime engine executes entirely via the command line interface. It ingests the raw candidate data stream, scores the profiles using the local model, attaches the cached justifications, and writes out the finalized shortlist.

Run the execution pipeline using the following command:

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv

```

### Operational Execution Flow inside `rank.py`:

* **Asset Loading:** Loads `ranker.pkl` and maps `reasoning_cache.json` into memory instantly.
* **Line-by-Line Stream Ingestion:** Streams the candidates to prevent system memory spikes.
* **Honeypot and Filter Interception:** Evaluates experience out-of-bounds, job-hopping histories, and consulting-firm exclusions. Failed profiles are short-circuited to a `0.0` score.
* **LightGBM Prediction:** Passing profiles are converted to numerical matrices and evaluated by the model.
* **Deterministic Sorting:** Orders candidates descending by score, applying an ascending alphabetical sort on `candidate_id` as a definitive tiebreaker.
* **Justification Mapping:** Slices the top 100 entries, pulls their corresponding sentences from the reasoning cache, and saves the file.

---

## Output Data Schema

The generated `submission.csv` file targets exactly the top 100 ranked candidates and contains the following structured attributes:

* `candidate_id` (String): The unique identification token assigned to the profile.
* `score` (Float): The composite evaluation metric predicted by the model, rounded to 4 decimal places.
* `rank` (Integer): The final ordered sequential position on the leaderboard.
* `reasoning` (String): The pre-computed 1-2 sentence factual hiring justification detailing specific skills, years of experience, or operational gaps.