# 🛡️ Z-AUDIT: Domain-Aware AI Fraud Analytics Engine

![React](https://img.shields.io/badge/Frontend-React-blue) ![FastAPI](https://img.shields.io/badge/Backend-FastAPI-green) ![AI](https://img.shields.io/badge/AI-Groq%20%7C%20ChatGPT-orange) ![Diarization](https://img.shields.io/badge/Voice-Pyannote%20Audio-violet)

**Z-AUDIT** is an advanced AI-powered audio quality auditing system built specifically for large-scale field survey operations (targeting Indian trilingual survey contexts). It automates the detection of surveyor fraud, mimicking, and forced surveys by deeply analyzing audio recordings, transcripts, and agent behavioral history.

---

## 🚀 Key Features

### 🧠 Domain-Aware Fraud Detection
Unlike generic LLM analyzers that flag false positives, Z-AUDIT uses a **custom prompt architecture and preprocessing pipeline** tailored for trilingual Indian surveys:
- **Trilingual Speech Tolerance**: Automatically tolerates high surveyor speech limits (60-75%) caused by reading questions in three languages.
- **Upload Task Filtering**: Preprocessing engines automatically slice out non-spoken tasks (like "upload photo") to prevent false "unanswered question" penalties.
- **Physical Viability Testing**: Calculates if average question duration is physically possible to read out loud.

### 🎙️ Machine-Level Voice Diarization
Integrates with **Pyannote Audio API** and **Groq Whisper Large v3** to separate voices:
- Hard-detects actual speaker counts instead of relying on LLM guesses.
- Combines Whisper transcripts with Pyannote speaker mapping for 100% accurate turn-taking analysis.

### 🕵️ Agent Risk Profiling & Cross-Call Memory
A built-in `agent_profiler` calculates an Agent's rolling historical risk:
- Tracks total calls, flagged calls, and calculates a **Composite Risk Score (0-10)**.
- Scans the database to detect if surveyors are copying and pasting identical answers across multiple different respondents.
- Injects this historical risk context *directly into the LLM prompt* for subsequent calls.

### ⚡ Zero-Cost ChatGPT Bypass Automation
To circumvent Groq rate limits without paying for OpenAI API credits, Z-AUDIT features a specialized Playwright sub-system (`chatgpt_browser.py`) that boots an isolated Chrome profile, visually interfaces with ChatGPT, pastes the survey payload, and parses the streaming JSON result entirely in the background.

### 📊 React Command Dashboard
A highly polished, glassmorphism-themed frontend that offers:
- **Agent Leaderboard**: Rank and filter high-risk agents instantly.
- **Cross-Call Heatmap**: Area charts to track fraud occurrences dynamically over time.
- **Detailed Audit Views**: View the specific prompt, JSON response, exact timestamps of fraud evidence, and speaker analysis for every single call.

---

## 🏗️ Architecture Stack

- **Frontend**: React (Vite), TailwindCSS, Recharts
- **Backend**: Python 3.11, FastAPI, SQLAlchemy (SQLite), Playwright (for browser automation)
- **AI Models**: 
  - *Audio*: Groq Whisper Large v3, Pyannote Speaker Diarization
  - *Analysis*: LLaMA 3.3 70B (via Groq) OR ChatGPT 4o (via Playwright Automation)

---

## 🚦 Quick Start Guide

### 1. Prerequisites
- Python 3.11+
- Node.js 18+
- [Groq API Key](https://console.groq.com) (Free)
- [HuggingFace Token](https://huggingface.co/settings/tokens) (Free, for Pyannote Speaker Diarization)

### 2. Backend Setup
```bash
# Navigate to backend
cd backend

# Create virtual environment and install dependencies
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Create .env file and add your keys
echo "GROQ_API_KEY=your_groq_key_here" > .env
echo "HF_TOKEN=your_huggingface_token_here" >> .env

# Start FastAPI server
python -m uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
# Navigate to frontend in a new terminal
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```
Visit **http://localhost:5173** to view the live dashboard.

---

## 📁 Project Structure

```text
z-audit/
├── backend/
│   ├── main.py                  # FastAPI Application Routes & API
│   ├── fraud_detection.py       # LLM Prompts & Score Calibration
│   ├── preprocessing.py         # Filtering & Validation Logic
│   ├── agent_profiler.py        # Historical Scoring & Cross-Call DB Queries
│   ├── speaker_analysis.py      # Pyannote API integration
│   ├── transcription.py         # Groq Whisper integration
│   ├── chatgpt_browser.py       # Playwright ChatGPT bypass integration
│   └── models.py                # Database ORM classes
├── frontend/
│   ├── src/
│   │   ├── api.js               # API service layer
│   │   ├── App.jsx              # Application Shell
│   │   └── components/
│   │       ├── Dashboard.jsx        # Main Dashboard
│   │       ├── AgentLeaderboard.jsx # Ranking Table
│   │       ├── CrossCallHeatmap.jsx # Trend charts
│   │       ├── RecordDetail.jsx     # Deep dive JSON view
│   │       └── UploadModal.jsx      # Batch Excel / Audio ingestion 
└── Z-AUDIT_Architecture.md      # Comprehensive internal system documentation
```

---

*Z-AUDIT | Built by Zeex AI | IIT Madras Research Park | 2026*
