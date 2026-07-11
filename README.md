# HCP CRM Frontend + AI Agent

**AI-Powered Pharmaceutical HCP CRM System**  
*Streamlining field sales interactions with Healthcare Professionals using modern React frontend and LangGraph + Groq AI backend.*

---

## Overview

This project is a **full-stack CRM application** designed specifically for pharmaceutical field sales representatives to manage interactions with Healthcare Professionals (HCPs).

It combines:
- A modern, responsive **React + Vite frontend** with Tailwind CSS and data visualization
- A powerful **FastAPI + LangGraph AI Agent backend** that provides intelligent assistance for logging visits, generating reports, and extracting insights

The system helps reps log calls, track engagement, generate compliant reports, and get AI-powered summaries and entity extraction from natural language notes.

---

## Key Features

### Frontend (React)
- Clean, professional dashboard interface for HCP management
- Interactive charts using **Recharts** (engagement trends, prescribing scores, etc.)
- Real-time interaction logging form
- HCP search and history view
- Responsive design with **Tailwind CSS** and **Lucide React** icons
- Built with **React 19** and **Vite 8** for excellent performance

### Backend AI Agent (Python)
- **LangGraph ReAct Agent** with 6 specialized tools:
  1. `log_interaction` - Intelligent logging with AI entity extraction & sentiment analysis
  2. `edit_interaction` - Update previous records with automatic re-analysis
  3. `search_hcp` - Smart HCP search and filtering
  4. `get_hcp_history` - Complete interaction timeline + analytics
  5. `generate_call_report` - Pharma-compliant formal report generation
  6. `extract_entities_from_text` - NER for products, conditions, competitors, etc.

- Powered by **Groq** (fast & smart LLM models)
- In-memory data store (easily replaceable with PostgreSQL/MySQL)
- Structured + conversational interfaces

### AI Capabilities
- Automatic entity extraction (products, medical conditions, competitors, action items)
- Sentiment analysis on interaction notes
- AI-generated professional summaries
- Pharma-compliant call report generation
- Natural language understanding for visit logging

---

## Tech Stack

### Frontend
- **React 19** + **Vite 8**
- **Tailwind CSS 4**
- **Recharts** for visualizations
- **Lucide React** icons
- ESLint + TypeScript-ready

### Backend
- **FastAPI**
- **LangGraph** + **LangChain**
- **Groq** (LLM inference)
- **Python 3.11**

### Development Tools
- PostCSS + Tailwind
- Modern ESLint flat config

---

## Project Structure
hcp-crm-frontend/
├── src/
│   ├── App.jsx              # Modern dashboard with Recharts + Lucide
│   ├── main.jsx
│   └── index.css
├── index.html
├── vite.config.js
├── package.json
├── postcss.config.js
├── tailwind.config (via PostCSS)
├── eslint.config.js
└── hcp_crm_agent.py         # Backend AI Agent


---

## Getting Started

### Prerequisites
- Node.js 20+
- Python 3.11+
- Groq API Key

### Frontend Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev


# Install dependencies (via script header or manually)
pip install fastapi langgraph langchain-groq uvicorn

# Set environment variables
export GROQ_API_KEY=your_groq_key_here
export PORT=8000

# Run the agent
python hcp_crm_agent.py

The backend runs on http://localhost:8000 with interactive API docs at /docs.

Available Endpoints
Agent Chat

POST /agent/chat - Conversational interface with the AI agent

Interactions

POST /interactions/log - Structured logging
GET /interactions - List interactions
GET /interactions/{id} - Get specific interaction
PUT /interactions/{id} - Edit interaction

HCPs

GET /hcps - Search HCPs
GET /hcps/{id} - Get HCP details
GET /hcps/{id}/history - Full history + analytics

Reports & Tools

POST /interactions/{id}/report - Generate call report
POST /extract-entities - Entity extraction
GET /status - System health


Sample Usage
Conversational Example:
"Log a visit with Dr. Sarah Chen. Discussed Cardivex, left 6 samples. She showed strong interest and has concerns about Medicare reimbursement."
The agent will automatically:

Identify the HCP
Extract entities
Analyze sentiment
Generate AI summary
Log the interaction


Data Models
HCP Record

ID, Name, Specialty, NPI, Institution, Territory, Tier
Prescribing & Engagement Scores

Interaction Record

Full audit trail including AI summary, sentiment, entities, samples left, follow-up dates, etc.


Future Enhancements

Database integration (PostgreSQL + SQLAlchemy)
Authentication & user management for multiple reps
Real-time updates with WebSockets
Advanced analytics dashboard
Mobile-responsive improvements
Export to PDF/CRM systems
Integration with external pharma data sources


License
This project is for demonstration and educational purposes. Proprietary pharmaceutical CRM logic is included as example data.

Contributing
Contributions are welcome! Please fork the repository and submit pull requests for:

New frontend components
Additional agent tools
Better visualizations
Test coverage


Built with ❤️ for the future of intelligent pharma sales enablement.
AI Agent + Modern Frontend = Next-Gen HCP Relationship Management
text
