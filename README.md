# Smart AI Candidate Ranking System

An AI-driven recruitment pipeline that understands candidate context, career progression, and platform signals to rank applicants semantically against job descriptions.

## Team Members
- Shantanu Bhatnagar (AI & LLM Lead)
- Tatini (UI/UX Developer)
- Hansika (Data Extraction)
- Vihaan (Data Extraction)

## Architecture
- **Data Layer:** Extracts and cleans raw text from candidate portfolio PDFs.
- **AI Engine:** Generates HuggingFace semantic embeddings and applies mathematical scoring + LLM summarization.
- **UI Interface:** Interactive recruiter dashboard displaying a tiered leaderboard.

## Setup Instructions
1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application