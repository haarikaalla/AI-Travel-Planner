#  AI Travel Planner

[![CI](https://github.com/haarikaalla/AI-Travel-Planner/actions/workflows/ci.yml/badge.svg)](https://github.com/haarikaalla/AI-Travel-Planner/actions)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-purple)
![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-green)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

> A production-grade multi-agent AI travel planner built with **LangGraph**, **LangChain**, and **Ollama**.  

---

##  What It Does

Enter your destination, duration, budget, and interests — and watch **9 AI agents** collaborate in real time to generate a complete, personalized travel plan including:

-  **Day-by-day itinerary** with timed activities, insider tips & costs
-  **Weather & climate** analysis with best months to visit
-  **Accommodation options** across budget, mid-range, and luxury
-  **Food guide** — must-try dishes, restaurants, markets
-  **Budget breakdown** with money-saving hacks and tipping culture
-  **Smart packing list** tailored to your destination and activities
-  **PDF + TXT export** of your full itinerary

---

##  Architecture

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   LangGraph State Machine                │
│                                                          │
│  ① Supervisor ──────────────────────────────────────    │
│       │                                                  │
│  ② Researcher (destination intel)                        │
│       │                                                  │
│  ┌────┴────────────────────────────────────────────┐    │
│  ③ Weather  ④ Accommodation  ⑤ Activities  ⑥ Food  ⑦ Budget  (parallel)
│  └────┬────────────────────────────────────────────┘    │
│       │                                                  │
│  ⑧ Packing Agent (uses weather output)                   │
│       │                                                  │
│  ⑨ Composer (assembles all outputs into final result)    │
│                                                          │
└─────────────────────────────────────────────────────────┘
    │
    ▼
Beautiful Streamlit UI (6 tabs + PDF download)
```

**Key patterns demonstrated:**
-  Supervisor-worker orchestration
-  Parallel agent fan-out (5 agents run after researcher)
-  Agent state sharing via LangGraph `TypedDict`
-  `Annotated` list merging for parallel outputs
- Retry logic with graceful fallback generators
-  3-strategy JSON parser (handles messy LLM output)
-  LangChain + Ollama local LLM integration

---

## Quick Setup

### 1. Install Ollama 

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows — download from https://ollama.ai/download
```

### 2. Pull a model

```bash
ollama pull llama3.2       # 2GB — recommended (fast)
# OR
ollama pull llama3         # 4.7GB — better quality
# OR
ollama pull mistral        # 4.1GB — alternative
```

### 3. Start Ollama
```bash
ollama serve
# If you see "address already in use" — Ollama is already running 
```

### 4. Clone & install

```bash
git clone https://github.com/haarikaalla/AI-Travel-Planner.git
cd AI-Travel-Planner

python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 5. Run

```bash
streamlit run app.py
```

Open **http://localhost:8501** 

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Agent Orchestration** | LangGraph (StateGraph, parallel fan-out, END) |
| **LLM Framework** | LangChain + langchain-ollama |
| **Local LLM** | Ollama (Llama 3.2 / Mistral / Phi-3) |
| **Frontend** | Streamlit (dark theme, 6-tab layout) |
| **PDF Export** | ReportLab |
| **State Management** | LangGraph TypedDict + Annotated merging |
| **CI/CD** | GitHub Actions |

---

##  Project Structure

```
AI-Travel-Planner/
├── app.py                    ← Streamlit UI (eye-catching dark theme, 6 tabs)
├── travel_graph.py           ← LangGraph multi-agent pipeline (9 agents)
├── pdf_export.py             ← ReportLab PDF generator
├── requirements.txt          ← Python dependencies
├── .env.example              ← Environment variable template
├── .gitignore                ← Proper Python gitignore
├── .github/
│   └── workflows/
│       └── ci.yml            ← GitHub Actions CI (syntax + unit tests)
└── README.md
```

---

##  Configuration

Copy `.env.example` to `.env` and set your preferred model:

```bash
cp .env.example .env
```

```env
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

You can also select the model in the UI sidebar — no restart needed.

---

##  Troubleshooting

| Error | Fix |
|-------|-----|
| `Connection refused` | Run `ollama serve` in a terminal |
| `model not found` | Run `ollama pull llama3.2` |
| Slow generation | Normal on CPU (~3-5 min). GPU is 5-10x faster |
| Empty sections | Fallback data auto-fills — check agent log tab |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` inside venv |

---

##  Resume Impact

This project showcases:

| Skill | Where demonstrated |
|-------|-------------------|
| **LangGraph** | StateGraph, parallel edges, Annotated merging |
| **Multi-agent design** | Supervisor + 8 specialized workers |
| **LangChain** | OllamaLLM, prompt engineering |
| **Local LLM deployment** | Ollama with model switching |
| **Robust error handling** | Retry logic, fallback generators, 3-strategy JSON parser |
| **Production UI** | Streamlit, 6 tabs, agent tracker |
| **PDF generation** | ReportLab A4 document |
| **CI/CD** | GitHub Actions automated testing |
| **Software engineering** | Clean code, separation of concerns, typed state |

---

##  License

MIT 
