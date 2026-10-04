# AI Agent Firewall

Runtime security layer for AI agents. Detects PII, secrets, and prompt injections—blocks risky actions in real-time with transparent reasoning.

## Features

- **Real-time Security Monitoring** — Live dashboard showing all agent decisions
- **PII & Secret Detection** — Automatically identifies personal data and credentials
- **Prompt Injection Detection** — Catches malicious input attempts
- **Risk Scoring** — Transparent risk assessment with detailed reasoning
- **Data Auto-Deletion** — GDPR-compliant retention and deletion policies
- **Approval Workflows** — Approve/reject pending high-risk actions
- **Chat Interface** — Test agents and see security decisions in real-time
- **Audit Trail** — Complete event history for compliance

## Architecture

- **Backend:** FastAPI (Python) — Port 8000
- **Frontend:** Next.js 14 (React) — Port 3000
- **AI Engine:** Ollama with gemma4:e4b model — Port 11434
- **Database:** SQLite — Security events and policies

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Ollama (with gemma4:e4b model)

### Setup Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Backend runs at `http://localhost:8000`

### Setup Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`

### Start Ollama
```bash
ollama serve
```

Ensure `gemma4:e4b` model is available:
```bash
ollama pull gemma4:e4b
```

## Usage

### Dashboard
- Monitor all agent activity in real-time
- Approve or reject pending requests
- Filter by decision type (Blocked, Pending, All)
- Search agents and tools

### Chat Interface
Test agents conversationally and see security decisions with transparent reasoning.

### Privacy Dashboard
Manage data retention policies and verify deletion compliance.

## How It Works

1. **Integration**: Agent calls are routed through the firewall via WebSocket
2. **Analysis**: Firewall analyzes request for security risks
3. **Decision**: Risk score determines APPROVED / BLOCKED / APPROVE_WITH_REVIEW
4. **Logging**: All decisions and events recorded for audit trail

## Security Detections

| Detection | Purpose |
|-----------|---------|
| PII Detection | Identifies email, phone, SSN, credit cards |
| Secret Detection | Finds API keys, tokens, passwords |
| Prompt Injection | Detects malicious prompt patterns |
| Data Classification | Categorizes data sensitivity |

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI server
│   ├── requirements.txt      # Python dependencies
│   └── models/              # Security analysis models
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Dashboard
│   │   ├── chat/page.tsx    # Chat interface
│   │   ├── privacy/page.tsx # Data deletion dashboard
│   │   └── globals.css      # Theme and styling
│   ├── package.json
│   └── next.config.js
└── README.md
```

## Environment Variables

Backend (`.env`):
```
OLLAMA_API_URL=http://localhost:11434
DATABASE_URL=sqlite:///./security.db
```

Frontend (`.env.local`):
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Development

The project uses:
- **Tailwind CSS** — Utility-first styling
- **Recharts** — Data visualization
- **WebSockets** — Real-time communication
- **SQLite** — Lightweight persistence

## License

MIT

## Author

Luke

## Hackathon

Aveth's Forge Hackathon 2026 — Hyderabad
