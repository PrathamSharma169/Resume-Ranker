# Adaptive Multi-Stage Candidate Intelligence Engine

Built for the **Redrob Hackathon** by Team **Hack India**.

An **evidence-driven, explainable, and memory-constrained candidate ranking pipeline** designed to process large candidate datasets (up to 100,000+ profiles) and match them against complex job descriptions.

---

## 🚀 Key Features

- **Rolling Batch Processing**: Streams and evaluates candidates in rolling batches of **15,000**, carrying forward the Top 100 survivors to the next batch. Guarantees **O(K) memory** and prevents OOM crashes on huge datasets.
- **Full Multi-Stage Evaluation**: Every candidate is analyzed across 5 intelligence dimensions:
  - **Evidence Engine** — Fact-checks claims, validates durations, measures career stability.
  - **Authenticity Auditor** — Flags keyword stuffing, inconsistent timelines, suspicious profiles.
  - **Narrative Engine** — Analyzes career continuity, role progression, growth direction.
  - **Behavioral Profiler** — Evaluates completion metrics, notice periods, response rates.
  - **Recruitability Estimator** — Computes fit, salary alignment, and availability.
- **Deterministic Deduplication & Tie-Breaking**: Each candidate appears only once in the final ranking. Ties broken by `candidate_id` ascending.
- **Interactive Streamlit Dashboard**: Full transparency into pipeline decisions with downloadable results.

---

## 📁 Project Structure

```
Resume Ranker/
├── .gitignore
├── submission_metadata_template.yaml
│
└── candidate-ranking-system/          ← Main project directory
    ├── main.py                        ← CLI entrypoint
    ├── app.py                         ← Streamlit UI entrypoint
    ├── requirements.txt
    ├── job_description.docx           ← ⚠️ Place JD file HERE
    ├── sample_candidates.json         ← ⚠️ Place candidate file HERE
    ├── candidates.jsonl               ← ⚠️ Place full dataset HERE (for 100K run)
    ├── configs/                       ← YAML configuration files
    ├── models/                        ← Typed dataclasses (profiles, vectors, etc.)
    ├── src/
    │   ├── parser/                    ← JSONL/DOCX stream parsers
    │   ├── jd_engine/                 ← JD intelligence analyzer
    │   ├── engines/                   ← Feature extraction, scoring, ranking
    │   ├── pipeline/                  ← PipelineManager (central orchestrator)
    │   └── utils/                     ← Math, text, logging helpers
    └── ui/                            ← Streamlit pages and theme
```

---

## ⚠️ Important: File Placement

> **Both `job_description.docx` and the candidate file (`candidates.jsonl` or `sample_candidates.json`) must be placed in the same directory as `main.py`**, i.e. inside `candidate-ranking-system/`.
>
> The pipeline resolves file paths relative to this directory. Placing them elsewhere will cause a "file not found" error.

---

## 🛠️ Setup & Installation

```bash
# 1. Navigate to the project directory
cd candidate-ranking-system

# 2. Create and activate a virtual environment (recommended)
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## ▶️ Running the Pipeline (CLI)

Make sure you are inside the `candidate-ranking-system/` directory and that `job_description.docx` and your candidate file are placed there.

### Quick Run (sample dataset — 50 candidates):
```bash
python main.py --jd ./job_description.docx --candidates ./sample_candidates.json --out ./submission.csv
```

### Full Run (100K candidates):
```bash
python main.py --jd ./job_description.docx --candidates ./candidates.jsonl --out ./submission.csv
```

### CLI Options:
| Flag              | Description                                      | Default          |
|-------------------|--------------------------------------------------|------------------|
| `--jd`            | Path to job description `.docx` file             | Auto-detected    |
| `--candidates`    | Path to candidate `.jsonl` or `.json` file       | Auto-detected    |
| `--out`           | Path to save the final `submission.csv`          | `./submission.csv` |
| `--output`        | Directory for all output reports                 | `./data/output`  |
| `--top-k`         | Number of top candidates to rank                 | `100`            |
| `--no-embeddings` | Disable semantic embeddings (faster)             | Disabled         |

---

## 📊 Running the Streamlit Web App

```bash
cd candidate-ranking-system
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

### Dashboard Pages:
1. **Pipeline Dashboard** — Upload or specify local file paths, run the full pipeline, and download ranked results as CSV.
2. **Job Intelligence** — Visualize required vs. preferred competencies, experience constraints, and domain keywords extracted from the JD.
3. **Rankings Overview** — Full ranked table with score dimension progress bars.
4. **Candidate Explorer** — Inspect individual candidate profile cards with radar chart comparison against JD requirements.
5. **Explainability Viewer** — View decision traces, strengths, improvement areas, and module contributions for each candidate.

---

## 🔧 How the Ranking Works

```
Batch 1:  [15,000 new candidates]
  → Full evaluation (all 5 engines)
  → Top 100 survive → carry forward

Batch 2:  [15,000 new] + [100 carry-over] = 15,100
  → Full evaluation
  → Top 100 survive → carry forward

  ... repeats until all candidates processed ...

Final Batch:  [remaining] + [100 carry-over]
  → Full evaluation
  → Final Top 100 = submission output
```

Every single candidate is fully evaluated. The carry-over mechanism ensures the best candidates compete fairly across all batches.

---

## 👥 Team

| Name              | Role                                    | Email                           |
|-------------------|-----------------------------------------|---------------------------------|
| Pratham Sharma    | Backend Architect & Data Scientist      | prathamsharma1604@gmail.com     |
| Tanmay Sawankar   | Frontend Architect & Systems Engineer   | tanmaysawankar4441@gmail.com    |

---

## 📝 Reproduce Command

```bash
cd candidate-ranking-system
python main.py --jd ./job_description.docx --candidates ./sample_candidates.json --out ./submission.csv
```

This runs end-to-end in under 5 minutes on CPU with 16GB RAM and no network access.
