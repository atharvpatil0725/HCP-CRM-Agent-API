# /// script
# requires-python = "==3.11.*"
# dependencies = [
#   "codewords-client==0.4.10",
#   "fastapi==0.116.1",
#   "langgraph==1.2.9",
#   "langchain-groq==1.1.3",
#   "langchain-core==1.4.9",
#   "langchain==1.3.13",
#   "groq==0.37.1"
# ]
# [tool.env-checker]
# env_vars = [
#   "PORT=8000",
#   "LOGLEVEL=INFO",
#   "CODEWORDS_API_KEY",
#   "CODEWORDS_RUNTIME_URI",
#   "GROQ_API_KEY"
# ]
# ///

import asyncio
import os
import uuid
import json
from datetime import datetime
from typing import Any, Optional

from codewords_client import logger, run_service
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# ---------------------------------------------------------------------------
# Mock In-Memory Data Store  (replaces MySQL/Postgres for prototype)
# ---------------------------------------------------------------------------

HCPS: dict[str, dict] = {
    "hcp-001": {
        "id": "hcp-001", "name": "Dr. Sarah Chen", "specialty": "Cardiologist",
        "npi": "1234567890", "institution": "Northwestern Memorial Hospital",
        "territory": "Chicago North", "tier": "A",
        "email": "s.chen@nwmh.org", "phone": "+1-312-555-0100",
        "prescribing_score": 92, "engagement_score": 88,
        "created_at": "2024-01-15T09:00:00Z"
    },
    "hcp-002": {
        "id": "hcp-002", "name": "Dr. James Patel", "specialty": "Endocrinologist",
        "npi": "9876543210", "institution": "University of Chicago Medical Center",
        "territory": "Chicago South", "tier": "B",
        "email": "j.patel@uchicago.edu", "phone": "+1-312-555-0202",
        "prescribing_score": 74, "engagement_score": 65,
        "created_at": "2024-02-10T09:00:00Z"
    },
    "hcp-003": {
        "id": "hcp-003", "name": "Dr. Maria Torres", "specialty": "Primary Care Physician",
        "npi": "5678901234", "institution": "Rush University Medical Center",
        "territory": "Chicago West", "tier": "A",
        "email": "m.torres@rush.edu", "phone": "+1-312-555-0303",
        "prescribing_score": 88, "engagement_score": 91,
        "created_at": "2024-01-20T09:00:00Z"
    },
    "hcp-004": {
        "id": "hcp-004", "name": "Dr. Kevin Walsh", "specialty": "Neurologist",
        "npi": "3456789012", "institution": "Loyola University Medical Center",
        "territory": "Chicago West", "tier": "B",
        "email": "k.walsh@lumc.edu", "phone": "+1-708-555-0404",
        "prescribing_score": 61, "engagement_score": 55,
        "created_at": "2024-03-05T09:00:00Z"
    },
}

INTERACTIONS: dict[str, dict] = {
    "int-001": {
        "id": "int-001", "hcp_id": "hcp-001", "rep_id": "rep-001",
        "rep_name": "Alex Johnson", "interaction_type": "In-Office Visit",
        "date": "2025-06-15", "duration_minutes": 25,
        "products_discussed": ["Cardivex", "Lipitol"],
        "samples_left": {"Cardivex 10mg": 6},
        "objectives": "Present new REMS data for Cardivex; discuss Q2 patient outcomes",
        "outcomes": "HCP expressed strong interest. Requested follow-up with Q3 data.",
        "notes": "Dr. Chen raised concerns about Medicare reimbursement for Cardivex. She has 3 new hypertension patients considering the drug. Positive engagement overall.",
        "sentiment": "positive",
        "entities": {"products": ["Cardivex", "Lipitol"], "conditions": ["hypertension"],
                     "competitors": [], "action_items": ["Send Q3 REMS data", "Follow up re: Medicare"]},
        "ai_summary": "Productive in-office visit. Dr. Chen expressed positive interest in Cardivex based on REMS data. Key concern: Medicare reimbursement. Follow-up for Q3 study results. 3 new potential patients identified.",
        "follow_up_date": "2025-07-20", "status": "completed",
        "created_at": "2025-06-15T11:30:00Z", "updated_at": "2025-06-15T11:30:00Z"
    },
    "int-002": {
        "id": "int-002", "hcp_id": "hcp-001", "rep_id": "rep-001",
        "rep_name": "Alex Johnson", "interaction_type": "Phone Call",
        "date": "2025-05-20", "duration_minutes": 10,
        "products_discussed": ["Cardivex"], "samples_left": {},
        "objectives": "Check in on Cardivex patient outcomes",
        "outcomes": "Dr. Chen reported 2 patients doing well. Will consider for more patients.",
        "notes": "Brief call. Positive feedback on tolerability. No objections raised.",
        "sentiment": "positive",
        "entities": {"products": ["Cardivex"], "conditions": [], "competitors": [], "action_items": []},
        "ai_summary": "Brief follow-up call. Dr. Chen reports positive patient outcomes with Cardivex (2 patients). Willing to prescribe more broadly. No objections.",
        "follow_up_date": None, "status": "completed",
        "created_at": "2025-05-20T14:00:00Z", "updated_at": "2025-05-20T14:00:00Z"
    },
    "int-003": {
        "id": "int-003", "hcp_id": "hcp-002", "rep_id": "rep-001",
        "rep_name": "Alex Johnson", "interaction_type": "Conference",
        "date": "2025-06-01", "duration_minutes": 15,
        "products_discussed": ["GlucoSync"],
        "samples_left": {"GlucoSync 500mg": 10},
        "objectives": "Introduce GlucoSync at ADA conference booth",
        "outcomes": "Dr. Patel showed moderate interest. Wants comparative data before prescribing.",
        "notes": "Met Dr. Patel at ADA booth. Currently using competitor Metformin Plus. Requested our comparative efficacy data.",
        "sentiment": "neutral",
        "entities": {"products": ["GlucoSync"], "conditions": ["Type 2 Diabetes"],
                     "competitors": ["Metformin Plus"], "action_items": ["Send comparative efficacy data"]},
        "ai_summary": "Conference introduction at ADA. Dr. Patel currently uses Metformin Plus. Moderate interest in GlucoSync pending comparative efficacy data. 10 samples left.",
        "follow_up_date": "2025-07-01", "status": "completed",
        "created_at": "2025-06-01T10:00:00Z", "updated_at": "2025-06-01T10:00:00Z"
    },
}

# ---------------------------------------------------------------------------
# Groq LLM helpers
# ---------------------------------------------------------------------------

def get_fast_llm() -> ChatGroq:
    """openai/gpt-oss-20b - fast inference for chat and entity extraction."""
    return ChatGroq(model="openai/gpt-oss-20b", api_key=os.environ["GROQ_API_KEY"],
                   temperature=0.2, max_tokens=2048)

def get_smart_llm() -> ChatGroq:
    """openai/gpt-oss-120b - high-quality for report generation."""
    return ChatGroq(model="openai/gpt-oss-120b", api_key=os.environ["GROQ_API_KEY"],
                   temperature=0.3, max_tokens=4096)    
def _parse_json_response(raw: str, fallback: dict) -> dict:
    """Safely parse LLM JSON output, stripping code fences."""
    try:
        text = raw.strip()
        if "```" in text:
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception:
        return fallback

# ---------------------------------------------------------------------------
# Tool 1: log_interaction  (REQUIRED)
# ---------------------------------------------------------------------------

@tool
def log_interaction(
    hcp_id: str,
    interaction_type: str,
    date: str,
    duration_minutes: int,
    products_discussed: list[str],
    notes: str,
    objectives: str = "",
    outcomes: str = "",
    samples_left: dict = {},
    follow_up_date: str = "",
    rep_name: str = "Field Rep"
) -> str:
    """
    [TOOL 1 - REQUIRED] Log a new HCP interaction.
    Uses gemma2-9b-it LLM to:
      - Extract entities (products, conditions, competitors, action items)
      - Detect sentiment (positive / neutral / negative)
      - Generate a concise AI summary stored in the CRM record.
    Returns interaction ID, AI summary, sentiment, and extracted entities.
    """
    if hcp_id not in HCPS:
        return json.dumps({"error": f"HCP '{hcp_id}' not found. Available: {list(HCPS.keys())}"})

    hcp = HCPS[hcp_id]
    llm = get_fast_llm()

    extraction_prompt = f"""You are a pharmaceutical CRM assistant. Analyze this HCP interaction note and extract structured data.

HCP: {hcp['name']} ({hcp['specialty']})
Interaction Type: {interaction_type}
Products Discussed: {', '.join(products_discussed)}
Objectives: {objectives}
Outcomes: {outcomes}
Rep Notes: {notes}

Return ONLY valid JSON:
{{"sentiment": "positive"|"neutral"|"negative",
  "entities": {{"products": [], "conditions": [], "competitors": [], "action_items": []}},
  "ai_summary": "2-3 sentence professional summary"}}"""

    resp = llm.invoke([HumanMessage(content=extraction_prompt)])
    fallback = {
        "sentiment": "neutral",
        "entities": {"products": products_discussed, "conditions": [], "competitors": [], "action_items": []},
        "ai_summary": f"Interaction with {hcp['name']} on {date}. {notes[:120]}"
    }
    extracted = _parse_json_response(resp.content, fallback)

    interaction_id = f"int-{uuid.uuid4().hex[:6]}"
    now = datetime.utcnow().isoformat() + "Z"
    record = {
        "id": interaction_id, "hcp_id": hcp_id,
        "rep_id": "rep-001", "rep_name": rep_name,
        "interaction_type": interaction_type, "date": date,
        "duration_minutes": duration_minutes, "products_discussed": products_discussed,
        "samples_left": samples_left, "objectives": objectives, "outcomes": outcomes,
        "notes": notes,
        "sentiment": extracted.get("sentiment", "neutral"),
        "entities": extracted.get("entities", fallback["entities"]),
        "ai_summary": extracted.get("ai_summary", fallback["ai_summary"]),
        "follow_up_date": follow_up_date or None,
        "status": "completed", "created_at": now, "updated_at": now,
    }
    INTERACTIONS[interaction_id] = record
    logger.info("Interaction logged", id=interaction_id, hcp=hcp["name"])
    return json.dumps({"success": True, "interaction_id": interaction_id,
                       "ai_summary": record["ai_summary"], "sentiment": record["sentiment"],
                       "entities": record["entities"]})

# ---------------------------------------------------------------------------
# Tool 2: edit_interaction  (REQUIRED)
# ---------------------------------------------------------------------------

@tool
def edit_interaction(interaction_id: str, field: str, new_value: Any) -> str:
    """
    [TOOL 2 - REQUIRED] Edit a previously logged HCP interaction.
    Allowed editable fields: interaction_type, date, duration_minutes, products_discussed,
    samples_left, objectives, outcomes, notes, follow_up_date, status.
    If the 'notes' field is updated, re-runs gemma2-9b-it to regenerate the AI summary
    and sentiment automatically.
    Returns updated record delta.
    """
    if interaction_id not in INTERACTIONS:
        return json.dumps({"error": f"Interaction '{interaction_id}' not found"})

    allowed = ["interaction_type", "date", "duration_minutes", "products_discussed",
               "samples_left", "objectives", "outcomes", "notes", "follow_up_date", "status"]
    if field not in allowed:
        return json.dumps({"error": f"Cannot edit '{field}'. Allowed: {allowed}"})

    record = INTERACTIONS[interaction_id]
    old_value = record.get(field)
    record[field] = new_value
    record["updated_at"] = datetime.utcnow().isoformat() + "Z"

    if field == "notes" and new_value:
        hcp = HCPS.get(record["hcp_id"], {})
        re_prompt = f"""Re-analyze updated HCP interaction notes.
HCP: {hcp.get('name', 'Unknown')} ({hcp.get('specialty', '')})
Updated Notes: {new_value}
Products: {', '.join(record.get('products_discussed', []))}

Return ONLY valid JSON:
{{"sentiment": "positive"|"neutral"|"negative", "ai_summary": "2-3 sentence professional summary"}}"""
        resp = get_fast_llm().invoke([HumanMessage(content=re_prompt)])
        updated = _parse_json_response(resp.content, {})
        if updated.get("sentiment"):
            record["sentiment"] = updated["sentiment"]
        if updated.get("ai_summary"):
            record["ai_summary"] = updated["ai_summary"]

    logger.info("Interaction edited", id=interaction_id, field=field)
    return json.dumps({"success": True, "interaction_id": interaction_id,
                       "field_updated": field, "old_value": str(old_value),
                       "new_value": str(new_value), "ai_summary": record.get("ai_summary", "")})

# ---------------------------------------------------------------------------
# Tool 3: search_hcp
# ---------------------------------------------------------------------------

@tool
def search_hcp(query: str, specialty: str = "", territory: str = "", tier: str = "") -> str:
    """
    [TOOL 3] Search HCPs by name, specialty, territory, or tier.
    Returns ranked list of matching HCPs with engagement metrics.
    """
    results = []
    q = query.lower()
    for hcp in HCPS.values():
        score = 0
        if q and (q in hcp["name"].lower() or q in hcp["specialty"].lower() or q in hcp["institution"].lower()):
            score += 3
        if specialty and specialty.lower() in hcp["specialty"].lower():
            score += 2
        if territory and territory.lower() in hcp["territory"].lower():
            score += 2
        if tier and tier.upper() == hcp["tier"]:
            score += 1
        if score > 0 or not q:
            results.append({**hcp, "_score": score})
    results.sort(key=lambda x: (x.pop("_score"), x["engagement_score"]), reverse=True)
    logger.info("HCP search", query=query, count=len(results))
    return json.dumps({"hcps": results, "total": len(results)})

# ---------------------------------------------------------------------------
# Tool 4: get_hcp_history
# ---------------------------------------------------------------------------

@tool
def get_hcp_history(hcp_id: str, limit: int = 10) -> str:
    """
    [TOOL 4] Retrieve full interaction timeline for an HCP.
    Returns interactions newest-first plus trend analytics:
    sentiment trajectory, visit frequency, top products.
    """
    if hcp_id not in HCPS:
        return json.dumps({"error": f"HCP '{hcp_id}' not found"})
    records = sorted(
        [i for i in INTERACTIONS.values() if i["hcp_id"] == hcp_id],
        key=lambda x: x["date"], reverse=True
    )[:limit]
    sentiments = [r["sentiment"] for r in records]
    pos = sentiments.count("positive")
    trend = "improving" if pos > len(sentiments) / 2 else "stable" if records else "no data"
    products: dict[str, int] = {}
    for r in records:
        for p in r.get("products_discussed", []):
            products[p] = products.get(p, 0) + 1
    logger.info("HCP history", hcp_id=hcp_id, count=len(records))
    return json.dumps({
        "hcp": HCPS[hcp_id], "interactions": records,
        "analytics": {
            "total_interactions": len(records), "sentiment_trend": trend,
            "top_products": sorted(products.items(), key=lambda x: x[1], reverse=True)[:3],
            "last_interaction": records[0]["date"] if records else None
        }
    })

# ---------------------------------------------------------------------------
# Tool 5: generate_call_report
# ---------------------------------------------------------------------------

@tool
def generate_call_report(interaction_id: str) -> str:
    """
    [TOOL 5] Generate a comprehensive, pharma-compliant call report
    using llama-3.3-70b-versatile. Covers objectives, outcomes,
    samples accountability, competitive intelligence, action items,
    and compliance notes.
    """
    if interaction_id not in INTERACTIONS:
        return json.dumps({"error": f"Interaction '{interaction_id}' not found"})
    rec = INTERACTIONS[interaction_id]
    hcp = HCPS.get(rec["hcp_id"], {})
    prompt = f"""Generate a formal pharma-compliant call report:

HCP: {hcp.get('name')} | Specialty: {hcp.get('specialty')} | Tier: {hcp.get('tier')}
Date: {rec['date']} | Type: {rec['interaction_type']} | Duration: {rec['duration_minutes']} min
Products: {', '.join(rec.get('products_discussed', []))}
Objectives: {rec.get('objectives', 'N/A')}
Outcomes: {rec.get('outcomes', 'N/A')}
Notes: {rec.get('notes', 'N/A')}
Samples Left: {json.dumps(rec.get('samples_left', {}))}
Follow-up: {rec.get('follow_up_date', 'Not scheduled')}
AI Summary: {rec.get('ai_summary', '')}
Entities: {json.dumps(rec.get('entities', {}))}

Format with sections: ## Call Report, ### HCP Profile, ### Call Objectives,
### Discussion Summary, ### Key Insights & HCP Sentiment, ### Products & Samples,
### Competitive Intelligence, ### Action Items & Follow-up, ### Compliance Notes.
Be concise and pharma-industry appropriate."""
    response = get_smart_llm().invoke([HumanMessage(content=prompt)])
    logger.info("Call report generated", id=interaction_id)
    return json.dumps({"interaction_id": interaction_id, "report": response.content,
                       "generated_at": datetime.utcnow().isoformat() + "Z"})

# ---------------------------------------------------------------------------
# Tool 6: extract_entities_from_text
# ---------------------------------------------------------------------------

@tool
def extract_entities_from_text(text: str, context: str = "") -> str:
    """
    [TOOL 6] NER pipeline on free-form text using gemma2-9b-it.
    Extracts: pharma products, medical conditions, competitors,
    sentiment, key HCP quotes, action items, and compliance risk flags.
    """
    prompt = f"""Extract pharmaceutical entities from this text.
Context: {context or 'HCP field visit notes'}
Text: {text}

Return ONLY valid JSON:
{{"products": [], "conditions": [], "competitors": [], "sentiment": "positive"|"neutral"|"negative",
  "key_quotes": [], "action_items": [], "risk_flags": []}}"""
    resp = get_fast_llm().invoke([HumanMessage(content=prompt)])
    result = _parse_json_response(resp.content,
        {"products": [], "conditions": [], "competitors": [], "sentiment": "neutral",
         "key_quotes": [], "action_items": [], "risk_flags": []})
    logger.info("Entity extraction done", chars=len(text))
    return json.dumps({"extracted": result, "char_count": len(text)})

# ---------------------------------------------------------------------------
# LangGraph Agent
# ---------------------------------------------------------------------------

AGENT_TOOLS = [
    log_interaction, edit_interaction, search_hcp,
    get_hcp_history, generate_call_report, extract_entities_from_text
]

AGENT_SYSTEM_PROMPT = (
    "You are an AI assistant embedded in a pharmaceutical CRM system, specialized in managing "
    "Healthcare Professional (HCP) interactions for field sales representatives. "
    "Help reps log and edit visits, search HCPs, retrieve history, generate call reports, "
    "and extract entities from unstructured notes. "
    "Always be professional, pharma-industry appropriate, and concise. "
    "When a rep describes a visit in natural language, automatically identify the HCP, "
    "interaction type, products discussed, and call log_interaction."
)


def create_hcp_agent():
    """Instantiate a fresh LangGraph ReAct agent with all 6 HCP tools."""
    llm = get_fast_llm()
    return create_react_agent(llm, AGENT_TOOLS, prompt=AGENT_SYSTEM_PROMPT)

# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="HCP CRM Agent API",
    description="AI-First CRM HCP Module - LangGraph + Groq backend with 6 agent tools",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Pydantic I/O Models --

class ChatRequest(BaseModel):
    message: str = Field(..., description="Conversational message to the HCP CRM AI Agent",
                         example="Log a visit with Dr. Sarah Chen. Discussed Cardivex, left 6 samples.")
    session_id: str = Field(default="default", description="Session ID for conversation continuity")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="Agent's natural-language response")
    tool_calls: list[str] = Field(default=[], description="Names of tools invoked this turn")

class LogInteractionRequest(BaseModel):
    hcp_id: str = Field(..., description="HCP identifier", example="hcp-001")
    interaction_type: str = Field(..., description="Interaction type",
                                  json_schema_extra={"enum": ["In-Office Visit","Phone Call","Video Call","Conference","Email","CME Event"]})
    date: str = Field(..., description="Date (YYYY-MM-DD)", example="2025-07-11")
    duration_minutes: int = Field(default=20, description="Duration in minutes", ge=1, le=480)
    products_discussed: list[str] = Field(default=[], description="Products discussed")
    notes: str = Field(..., description="Rep interaction notes",
                       example="Dr. Chen showed interest in Cardivex REMS data. Left 6 samples.")
    objectives: str = Field(default="", description="Call objectives")
    outcomes: str = Field(default="", description="Call outcomes")
    follow_up_date: str = Field(default="", description="Follow-up date (YYYY-MM-DD)")
    rep_name: str = Field(default="Field Rep", description="Representative name")

class EditInteractionRequest(BaseModel):
    field: str = Field(..., description="Field to update", example="outcomes")
    new_value: Any = Field(..., description="New value for the field")

class AgentStatusResponse(BaseModel):
    status: str
    tools: list[str]
    hcp_count: int
    interaction_count: int
    models: dict

# -- Endpoints --

@app.post("/", response_model=ChatResponse)
async def root_chat(request: ChatRequest):
    """Main entry point - chat with the LangGraph HCP CRM agent."""
    return await agent_chat(request)

@app.post("/agent/chat", response_model=ChatResponse)
async def agent_chat(request: ChatRequest):
    """Chat with the LangGraph HCP CRM agent (conversational interface)."""
    logger.info("Agent chat", session=request.session_id, msg_len=len(request.message))
    agent = create_hcp_agent()
    result = await agent.ainvoke({"messages": [HumanMessage(content=request.message)]})
    messages = result.get("messages", [])
    reply = ""
    tool_calls_made: list[str] = []
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_made.append(tc.get("name", "unknown"))
        if (hasattr(msg, "content") and isinstance(msg.content, str)
                and msg.content and not (hasattr(msg, "tool_calls") and msg.tool_calls)):
            reply = msg.content
    return ChatResponse(reply=reply, tool_calls=tool_calls_made)

@app.post("/interactions/log")
async def log_interaction_structured(request: LogInteractionRequest):
    """Log a new HCP interaction via structured form (direct tool call, no agent overhead)."""
    logger.info("Structured log", hcp_id=request.hcp_id)
    result = await asyncio.to_thread(log_interaction.invoke, {
        "hcp_id": request.hcp_id, "interaction_type": request.interaction_type,
        "date": request.date, "duration_minutes": request.duration_minutes,
        "products_discussed": request.products_discussed, "notes": request.notes,
        "objectives": request.objectives, "outcomes": request.outcomes,
        "follow_up_date": request.follow_up_date, "rep_name": request.rep_name,
    })
    return json.loads(result)

@app.get("/interactions")
async def list_interactions(hcp_id: Optional[str] = None, limit: int = 20):
    """List all interactions, optionally filtered by HCP."""
    records = list(INTERACTIONS.values())
    if hcp_id:
        records = [r for r in records if r["hcp_id"] == hcp_id]
    records.sort(key=lambda x: x["date"], reverse=True)
    return {"interactions": records[:limit], "total": len(records)}

@app.get("/interactions/{interaction_id}")
async def get_interaction(interaction_id: str):
    """Get a specific interaction by ID."""
    if interaction_id not in INTERACTIONS:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return INTERACTIONS[interaction_id]

@app.put("/interactions/{interaction_id}")
async def update_interaction(interaction_id: str, request: EditInteractionRequest):
    """Edit a specific field in an existing interaction record."""
    logger.info("Edit interaction", id=interaction_id, field=request.field)
    result = await asyncio.to_thread(edit_interaction.invoke,
                                     {"interaction_id": interaction_id,
                                      "field": request.field, "new_value": request.new_value})
    return json.loads(result)

@app.get("/hcps")
async def list_hcps(search: str = "", specialty: str = "", territory: str = "", tier: str = ""):
    """Search and list HCPs."""
    result = await asyncio.to_thread(search_hcp.invoke,
                                     {"query": search, "specialty": specialty,
                                      "territory": territory, "tier": tier})
    return json.loads(result)

@app.get("/hcps/{hcp_id}")
async def get_hcp(hcp_id: str):
    """Get HCP details."""
    if hcp_id not in HCPS:
        raise HTTPException(status_code=404, detail="HCP not found")
    return HCPS[hcp_id]

@app.get("/hcps/{hcp_id}/history")
async def get_hcp_history_endpoint(hcp_id: str, limit: int = 10):
    """Full interaction history and analytics for an HCP."""
    result = await asyncio.to_thread(get_hcp_history.invoke, {"hcp_id": hcp_id, "limit": limit})
    return json.loads(result)

@app.post("/interactions/{interaction_id}/report")
async def get_call_report(interaction_id: str):
    """Generate a comprehensive call report using llama-3.3-70b-versatile."""
    result = await asyncio.to_thread(generate_call_report.invoke, {"interaction_id": interaction_id})
    return json.loads(result)

@app.post("/extract-entities")
async def extract_entities_endpoint(request: dict):
    """Extract pharma entities from free-form text."""
    result = await asyncio.to_thread(extract_entities_from_text.invoke,
                                     {"text": request.get("text", ""),
                                      "context": request.get("context", "")})
    return json.loads(result)

@app.get("/status", response_model=AgentStatusResponse)
async def agent_status():
    """Agent health check - tools, counts, and LLM models."""
    return AgentStatusResponse(
        status="healthy",
        tools=[t.name for t in AGENT_TOOLS],
        hcp_count=len(HCPS),
        interaction_count=len(INTERACTIONS),
       models={"fast": "openai/gpt-oss-20b", "smart": "openai/gpt-oss-120b"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), loop="asyncio")