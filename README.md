# NIRF Analytics & Visualization Platform

An interactive conversational analytics and visualization platform for exploring India's **National Institutional Ranking Framework (NIRF)** dataset across **2017–2025**.

Unlike standard LLM wrappers that compute numbers in text and risk hallucinations, this platform pairs **LLM-based query planning and synthesis** with a **deterministic Python/Pandas analytics engine**, **FAISS semantic RAG** over official NIRF methodology documents, **claim-level empirical verification**, and **interactive Plotly visualizations**.

---

## Key Features

- **Natural Language Query Parsing**: Translates free-form questions into validated Pydantic execution plans (`QueryPlan`) with canonical NIRF category aliasing (e.g., resolving `"research"` → `"Research Institutions"`).
- **Deterministic Analytics Engine**: Executes exact statistical and longitudinal computations in Python/Pandas/NumPy/SciPy across 10 analytical modules (cohort performance, institutional trends, rank movements, state-level geography, score distributions, parameter correlations, outlier detection, rank transitions, and category evolution).
- **Semantic RAG & Grounded Synthesis**: Retrieves official NIRF parameter formulas and methodology passages from a local **FAISS** vector index built with `sentence-transformers`, producing cited responses.
- **Claim Verification & Anti-Hallucination**: Extracts numerical claims from generated answers and audits them against analytical execution outputs before rendering.
- **Interactive Plotly Visualizations**:
  - **Lollipop Charts** & **Horizontal Bar Charts** (with dynamic height scaling for full 50–100+ institution cohorts and abbreviated institutional labels)
  - **Score Distribution Histograms** & **Box & Whisker Plots** (with quartiles, IQR, whiskers, and hoverable institution points)
  - **Longitudinal Trend Lines** (with inverted rank axes so Rank #1 sits at the top and non-interpolated gaps for unranked years)
  - **Scatter Plots**, **Grouped Parameter Bars**, **Interactive Maps of India** (dot markers with hover tooltips), and **CSV-Exportable Tables**
- **Multi-Turn Conversation Memory**: Persists chat sessions, query plans, and active context in **SQLite**.

---

## Architecture

For a full pipeline walkthrough, component breakdown, and technology rationale, see [SYSTEM_ARCHITECTURE_AND_TECH_STACK.md](./SYSTEM_ARCHITECTURE_AND_TECH_STACK.md).

```text
User Query
  ├──► Intent Router & SQLite Conversation Memory (src/conversation/, src/conversational/)
  ├──► Query Parser & Validator (src/query_engine/)
  ├──► Semantic RAG over NIRF Docs via FAISS (src/rag/)
  ├──► Deterministic Analytics Engine via Pandas/SciPy (src/analytics/, src/execution/)
  ├──► Grounded Response Generator & Claim Verifier (src/response/)
  └──► Chart Planner & Plotly Renderer (src/visualization/)
```

---

## Project Structure

```text
DHV Project/
├── run.sh                                  # One-click Streamlit launcher script
├── requirements.txt                        # Python dependencies
├── pytest.ini                              # Pytest configuration
├── cleaning_script.py                      # Raw NIRF dataset cleaning pipeline
├── SYSTEM_ARCHITECTURE_AND_TECH_STACK.md   # Detailed architecture & tech stack guide
├── NIRF_Final_Cleaned_Dataset/             # Cleaned 2017–2025 NIRF data & audit reports
├── data/                                   # Runtime datasets & RAG index artifacts
├── docs/                                   # Phase-by-phase technical & evaluation docs
├── knowledge_base/                         # Source NIRF methodology documentation
├── scripts/
│   └── nirf_query_playground.py            # Main Streamlit web application
├── src/
│   ├── analytics/                          # Statistical & longitudinal computation modules
│   ├── conversation/                       # SQLite session & turn persistence
│   ├── conversational/                     # Intent routing & follow-up handling
│   ├── data/                               # Dataset loader & comparability validator
│   ├── execution/                          # DAG execution engine & result schemas
│   ├── llm/                                # Ollama / Gemma LLM client wrapper
│   ├── query_engine/                       # NL-to-QueryPlan parser & validator
│   ├── rag/                                # Chunker, embedder, FAISS vector store, retriever
│   ├── response/                           # Answer synthesis, claim extraction & verification
│   └── visualization/                      # Chart planner, Plotly renderer & India geo data
└── tests/                                  # Unit, integration, and visualization test suite
```

---

## Quick Start

### 1. Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) running locally (or configured via `OLLAMA_HOST` / `OLLAMA_MODEL`)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a local `.env` file (ignored by Git) using `.env.example` as a template and configure your local LLM settings.

### 4. Run the Web Application
Using the launcher script:
```bash
chmod +x run.sh
./run.sh
```
Or directly with Streamlit:
```bash
streamlit run scripts/nirf_query_playground.py --server.port 8501
```
Then open **http://localhost:8501** in your browser.

---

## Running Tests

Run the visualization and validation tests:
```bash
pytest tests/test_visualization.py tests/test_map_visualization.py tests/test_query_validator.py
```

---

## Example Questions to Try

- `give me ranking of all engineering colleges in 2024, generate a lollipop graph to show`
- `show horizontal graph of top 10 engineering colleges in 2025`
- `box plot of scores in university category for 2024`
- `show score histogram for research institutions in 2025`
- `scatter plot of TLR vs RPC for top 20 universities in 2024`
- `trend of IIT Madras in Engineering from 2018 to 2025`
- `show top 15 colleges in overall category on map in 2025`
- `which categories existed in NIRF 2017 and what new categories were introduced by 2025`

