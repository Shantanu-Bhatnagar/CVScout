# CVScout: High-Performance Candidate Evaluation Pipeline

This repository contains the core architecture for a memory-bounded, CPU-optimized talent evaluation engine designed to ingest large-scale candidate datasets, analyze professional history semantically, and rank candidates based on a composite evaluation of text alignment and platform behavioral signals.

Unlike traditional resume screening tools that rely on fragile keyword filters, this system evaluates the underlying context of a candidate's profile against a target job description. The engine operates entirely locally, maximizing processing speed and eliminating external network runtime dependencies.

## Technical Architecture and Optimization Features

The backend engine is engineered to sustain heavy data volumes under strict execution constraints:

* **Local Sparse Vectorization:** To bypass the compute overhead of deep transformer models on standard hardware, the engine processes textual data using a stateless token hashing vectorizer paired with sparse matrix dot products. Semantic alignment is computed locally on CPU architectures without requiring GPU acceleration or third-party API keys.
* **Bounded-Memory Streaming:** Ingesting large JSON structures entirely into memory presents severe risks of system out-of-memory crashes. This pipeline utilizes a rolling buffer decoder to parse and evaluate records iteratively, maintaining a completely flat and stable memory footprint regardless of the file size.
* **Deterministic Tie-Breaking:** The sorting layer enforces strict mathematical consistency. Profiles are sorted descending by their final composite evaluation score. In the event of an identical score, a secondary ascending alphabetical sort is applied to the unique candidate ID to settle rankings definitively.

## Tech Stack

The application relies entirely on a lightweight, performant scientific computing and data analysis stack:

* **Python 3.8+**: Core runtime environment.
* **scikit-learn**: Stateless text tokenization, hashing, and feature extraction via `HashingVectorizer`.
* **SciPy**: Efficient allocation and dot-product execution via Compressed Sparse Row (`csr_matrix`) structures.
* **NumPy**: High-speed, vectorized array operations for score blending.
* **Pandas**: Structured dataset management, alignment filtering, and tabular sorting.
* **Streamlit**: Light, high-performance web interface for recruiter interaction and data visualization.


## Directory Layout

```text
Ai-Candidate-Ranker/
│
├── data/
│   ├── raw_resumes/            # Location for candidate JSON source data
│   └── job_description.txt     # Plain text file containing the target job description
│
├── data_layer/
│   └── extractor.py            # Iterative JSON stream reader and text cleaning scripts
│
├── ai_engine/
│   └── rank.py                 # Core local text vectorization and hybrid scoring engine
│
├── ui_layer/
│   └── app.py                  # Streamlit interface for recruiter visualization
│
├── requirements.txt            # Project dependencies and scientific library versions
└── README.md                   # System documentation

```

---

## Setup and Installation

### 1. Environment Configuration

Install the required data processing and text analysis dependencies inside your environment:

```bash
pip install -r requirements.txt

```

### 2. Execution and Usage

The main ranking script is executed via the command line. You can customize the evaluation weights dynamically using the execution flags:

```bash
python ai_engine/rank.py \
    --candidates data/raw_resumes/candidates.json \
    --job-description data/job_description.txt \
    --output ranked_output.csv \
    --alpha 0.6 \
    --chunk-size 5000

```

### Command Parameters:

* `--candidates`: Path to the raw candidate source dataset file.
* `--job-description`: Path to the raw text file containing the target role parameters.
* `--output`: Target path and filename for the compiled evaluation metrics.
* `--alpha`: The scoring weight balance ratio. A setting of `0.6` assigns a 60 percent mathematical weight to semantic text alignment and a 40 percent weight to behavioral platform signals.
* `--chunk-size`: The batch limit for streaming records into memory during a single calculation loop.

---

## Output Data Schema

The scoring script outputs a standardized, structured CSV file designed for immediate parsing by downstream visualization UI components or testing frameworks. The exported data contains the following explicit attributes:

* `candidate_id` (String): The unique identification token assigned to the candidate profile.
* `score` (Float): The computed composite evaluation score, rounded to 4 decimal places.
* `rank` (Integer): The final sorted sequential position on the talent leaderboard after primary scores and deterministic tie-breaker constraints are resolved.