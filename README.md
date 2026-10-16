# TruthGuard AI

> **Claim-Level Evidence Verification Framework for Hallucination Mitigation in Question Answering over Academic Regulations and Examination Policies**

---

## 1. Overview & Core Architecture

TruthGuard AI implements an evidence verification pipeline designed to eliminate hallucinations when answering questions about university policies and examination regulations. Answers are never blindly trusted: every response is decomposed into atomic claims, each claim is independently verified against retrieved regulation clauses using an NLI cross-encoder, and a calibrated risk score determines whether to release the answer with verifiable citations or abstain with an explicit reason code.

```
                              ┌──────────────────────────────────────────────┐
                              │                 User Query                   │
                              └──────────────────────┬───────────────────────┘
                                                     │
                                                     ▼
                                      ┌──────────────────────────────┐
                                      │       Retriever Agent        │
                                      │   (BGE Embeddings + BM25     │
                                      │   Reciprocal Rank Fusion)    │
                                      └──────────────┬───────────────┘
                                                     │ Passages (Premises)
                           ┌─────────────────────────┴─────────────────────────┐
                           ▼                                                   ▼
            ┌──────────────────────────────┐                   ┌───────────────────────────────┐
            │       Generator Agent        │                   │    (Verifier Context Isolation│
            │  (Gemini - Policy Grounded)  │                   │     Independent from Agent)   │
            └──────────────┬───────────────┘                   └───────────────┬───────────────┘
                           │ Draft Answer                                      │
                           ▼                                                   │
            ┌──────────────────────────────┐                                   │
            │    Claim Extractor Agent     │                                   │
            │  (Atomic Claims + Typology)  │                                   │
            └──────────────┬───────────────┘                                   │
                           │ Atomic Claims {claim_i}                           │
                           └─────────────────────────┬─────────────────────────┘
                                                     │
                                                     ▼
                                      ┌──────────────────────────────┐
                                      │     Claim Verifier Agent     │
                                      │    (DeBERTa-v3 NLI Model     │
                                      │   Max Entailment / Contrad)  │
                                      └──────────────┬───────────────┘
                                                     │ Verified / Unsupported / Contradicted
                                                     ▼
                                      ┌──────────────────────────────┐
                                      │    Risk & Decision Agent     │
                                      │    Risk R = Σ w_i s_i / Σ w_i │
                                      │  Release vs Abstain (Reason) │
                                      └──────────────┬───────────────┘
                                                     │
                                                     ▼
                                      ┌──────────────────────────────┐
                                      │   Final Answer & Citations   │
                                      │    or Structured Abstention  │
                                      └──────────────────────────────┘
```

---

## 2. Models & Licences

| Component | Model Checkpoint | Licence | Description |
| :--- | :--- | :--- | :--- |
| **Claim Verifier (NLI)** | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | **MIT License** | DeBERTa-v3-base fine-tuned on MNLI, FEVER, and ANLI benchmarks for natural language inference. |
| **Embeddings** | `BAAI/bge-small-en-v1.5` | **Apache-2.0** | High-performance sentence-transformers dense embedding model (384-dim). |
| **LLM Generation & Extraction** | `Google Gemini` (Official SDK) | Commercial API | Policy answer generation and structured claim extraction. |

---

## 3. Hardware & Acceleration

- **Target Architecture**: Apple Silicon (M4, 24 GB Unified Memory).
- **Inference Engine**: PyTorch Metal Performance Shaders (`mps`) device acceleration with automatic CPU fallback.

---

## 4. Repository Layout

```
Truthai/
├── docker-compose.yml         # PostgreSQL 16 persistence container
├── Makefile                   # Automation targets (up, ingest, run, test, eval)
├── .env.example               # Configuration template
├── .gitignore                 # Secrets and artifact exclusions
├── README.md                  # Documentation and architecture guide
├── data/
│   ├── raw_pdfs/              # Original regulation PDFs (e.g. 2024-SEC-UG-REGULATIONS-1.pdf)
│   ├── processed/             # Extracted clauses, chunks, and ChromaDB vector store
│   └── gold/                  # Benchmark questions.csv (schema for dev/test splits)
├── prompts/                   # Versioned prompt templates
├── scripts/
│   ├── ingest.py              # Clause-aware PDF extraction and indexing
│   ├── verify_models.py       # Phase 0 hardware & model smoke test
│   ├── tune_thresholds.py     # Grid search for alpha, tau, theta_e, theta_c on DEV split
│   └── run_eval.py            # Evaluation benchmark on TEST split
├── backend/
│   ├── requirements.txt       # Python 3.11 dependencies
│   ├── app/
│   │   ├── api/               # FastAPI endpoints (POST /ask, GET /runs/{id})
│   │   ├── agents/            # LangGraph agents (Retriever, Generator, Verifier, Decision)
│   │   ├── schemas/           # Pydantic v2 data transfer records
│   │   ├── db/                # SQLAlchemy models and session handling
│   │   ├── retrieval/         # PyMuPDF/pdfplumber parser, ChromaDB, BM25 RRF
│   │   ├── verification/      # Batch DeBERTa-v3 NLI inference engine
│   │   ├── eval/              # Precision/Recall, Contradiction F1, Risk-Coverage, ECE
│   │   └── core/              # Config (pydantic-settings), logging, device
│   └── tests/                 # Unit and integration test suite
└── frontend/                  # Next.js + TypeScript + Tailwind UI
```

---

## 5. Quickstart & Commands

```bash
# 1. Setup Python 3.11 virtual environment
make setup

# 2. Configure environment
cp .env.example .env
# Edit .env with your GEMINI_API_KEY and DATABASE_URL

# 3. Start PostgreSQL
make up

# 4. Run tests
make test

# 5. Ingest regulation PDFs
make ingest

# 6. Start API server
make run

# 7. Run evaluation
make eval
```
# truth
