"""Tippmix Analyst MCP - research-only six-sport server on Render Free."""
from __future__ import annotations

import hmac
import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

TOKEN = os.environ.get("MCP_API_TOKEN", "")
HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
# Enabled by default; API usage is opt-in only after explicit configuration.
FREE_ONLY_MODE = os.environ.get("FREE_ONLY_MODE", "true").strip().lower() not in ("0", "false", "no")
if HOST and not TOKEN:
    raise RuntimeError("Set MCP_API_TOKEN in Render Environment")

SPORTS = {
    "football": "xG, xGA, recent form, strength of opponents, expected lineups; 90 minutes versus qualification",
    "basketball": "pace, ORtg, DRtg, shooting, injuries, rest; regulation versus overtime",
    "tennis": "surface, service holds, break points, returns, fitness, BO3/BO5",
    "american_football": "EPA/play, success rate, quarterback, offensive line, weather and overtime",
    "ice_hockey": "5v5 xG, high-danger chances, power play, penalty kill, expected goalkeeper, 60-minute versus overtime",
    "handball": "possessions, shot efficiency, goalkeeper, exclusions, absences, 60-minute settlement",
}
SYSTEM = """You are a research-only ST-First sports analyst.
Use ONLY source observations and named events supplied in the input.
No live Tippmix odds, injuries, sports stats, or matches can be verified by this server.
Do not invent data, odds, sources, probabilities, EV, ST scores, or A-rated picks.
Give zero to five candidates, and never produce bet recommendations.
ST evidence rubric F20/O20/H15/S20/K15/M10; M is model consistency.
Respond JSON only: {"candidates":[{"event_identifier":"...", "reason":"..."}],"notes":[]}.
An input odds value is NOT an independently verified current Tippmix price.
"""

mcp = FastMCP(
    "tippmix-analyst-mcp",
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=bool(HOST),
        allowed_hosts=[HOST] if HOST else [],
    ),
)

def analyze(sport: str, markets_json: str) -> dict[str, Any]:
    base = {
        "schema": "SPORT-CANDIDATE/1", "sport": sport,
        "verification": "RESEARCH_ONLY_NOT_INDEPENDENTLY_VERIFIED",
        "candidates": [], "execution": "no_model_call", "error": None,
        "notes": [],
    }
    try:
        data = json.loads(markets_json)
        assert isinstance(data, dict) and isinstance(data.get("markets"), list)
        assert len(data["markets"]) <= 50
    except (ValueError, AssertionError, TypeError):
        base["error"] = "INVALID_INPUT_MARKETS_JSON"
        return base

    records = {}
    for item in data["markets"]:
        if not isinstance(item, dict) or item.get("sport") not in (sport, None):
            continue
        eid = item.get("event_identifier")
        if not isinstance(eid, str) or not eid.strip():
            continue
        price = item.get("official_odds")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not (1.01 <= price <= 1000):
            price = None
        records[eid] = {
            "event_identifier": eid, "sport": sport, "event": item.get("event"),
            "event_start_hu": item.get("event_start_hu"),
            "market_exact": item.get("market_exact"), "selection": item.get("selection"),
            "observed_odds": price, "odds_source": item.get("source"),
            "observed_at_hu": item.get("observed_at_hu"),
            "evidence": item.get("evidence", []),
        }
    if not records:
        base["notes"] = ["No matching and identified supplied markets."]
        return base
    if FREE_ONLY_MODE:
        # No OpenAI API call, external statistics requests, or wagering action.
        # This is only a deterministic shortlist of caller-supplied observations.
        research = []
        excluded_below_odds = 0
        for record in records.values():
            price = record["observed_odds"]
            if price is not None and price < 1.80:
                excluded_below_odds += 1
                continue
            fields = ("event", "event_start_hu", "market_exact",
                      "selection", "odds_source", "observed_at_hu")
            complete = sum(bool(record.get(key)) for key in fields)
            entry = {key: value for key, value in record.items() if key != "evidence"}
            entry.update(
                st_score=None,
                st_tier="KUTATASI",
                status="NEM_HITELESITETT",
                research_data_coverage=complete,
                reason="Forrásellenőrzésre váró bemeneti megfigyelés; nem önálló statisztikai elemzés.",
                limitations=[
                    "No independent official classical Tippmix odds verification.",
                    "No independent statistics, injury or lineup validation.",
                    "No ST score, probability, EV or betting recommendation.",
                ],
            )
            research.append(entry)
        # Evidence coverage is NOT modeled win probability or an ST score.
        research.sort(key=lambda x: (-x["research_data_coverage"],
                                     x["event_identifier"]))
        base["candidates"] = research[:5]
        base["execution"] = "deterministic_free_only_no_api"
        base["notes"] = [
            "Zero external AI API calls; no usage-based model fees generated by this tool.",
            "Research candidates are not approved betting selections.",
            "Below-1.80 supplied odds excluded: " + str(excluded_below_odds),
            "Number of valid research observations considered: " + str(len(research)),
        ]
        return base
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("OPENAI_MODEL"):
        base["error"] = "OPENAI_API_NOT_CONFIGURED"
        return base
    try:
        from openai import OpenAI
        client = OpenAI(timeout=75, max_retries=1)
        result = client.responses.create(
            model=os.environ["OPENAI_MODEL"],
            instructions=SYSTEM + "\nSport-specific checks: " + SPORTS[sport],
            input=json.dumps({"sport": sport, "markets": list(records.values())}, ensure_ascii=False),
        )
        decoded = json.loads(result.output_text)
        chosen = decoded.get("candidates", []) if isinstance(decoded, dict) else []
        if not isinstance(chosen, list):
            chosen = []
        used = set()
        for suggestion in chosen:
            if not isinstance(suggestion, dict):
                continue
            eid = suggestion.get("event_identifier")
            if eid not in records or eid in used:
                continue
            entry = {key: value for key, value in records[eid].items() if key != "evidence"}
            entry.update(
                st_score=None, st_tier="KUTATASI", status="NEM_HITELESITETT",
                reason=str(suggestion.get("reason", "Research idea"))[:1000],
                limitations=["No independent official Tippmix market verification.",
                             "No independent statistics or lineup verification."],
            )
            base["candidates"].append(entry)
            used.add(eid)
            if len(base["candidates"]) == 5:
                break
        base["execution"] = "openai_responses_api_called"
    except Exception as exc:
        base["error"] = "MODEL_CALL_FAILED"
        base["notes"] = ["OpenAI model call failed.", "Error type: " + type(exc).__name__]
    return base


@mcp.tool()
def analyze_football(markets_json: str) -> dict:
    """Football: up to five research candidates from supplied data."""
    return analyze("football", markets_json)


@mcp.tool()
def analyze_basketball(markets_json: str) -> dict:
    """Basketball: up to five research candidates from supplied data."""
    return analyze("basketball", markets_json)


@mcp.tool()
def analyze_tennis(markets_json: str) -> dict:
    """Tennis: up to five research candidates from supplied data."""
    return analyze("tennis", markets_json)


@mcp.tool()
def analyze_american_football(markets_json: str) -> dict:
    """American football: up to five research candidates from supplied data."""
    return analyze("american_football", markets_json)


@mcp.tool()
def analyze_ice_hockey(markets_json: str) -> dict:
    """Ice hockey: up to five research candidates from supplied data."""
    return analyze("ice_hockey", markets_json)


@mcp.tool()
def analyze_handball(markets_json: str) -> dict:
    """Handball: up to five research candidates from supplied data."""
    return analyze("handball", markets_json)


@mcp.tool()
def get_capabilities() -> dict:
    """Report configuration and actual data capabilities without secrets."""
    return {
        "sports": list(SPORTS),
        "model_configured": bool(os.environ.get("OPENAI_API_KEY") and os.environ.get("OPENAI_MODEL")),
        "free_only_mode": FREE_ONLY_MODE,
        "external_ai_api_calls_enabled": not FREE_ONLY_MODE and bool(os.environ.get("OPENAI_API_KEY") and os.environ.get("OPENAI_MODEL")),
        "live_tippmix_odds_verified": False,
        "independent_sports_data_verified": False,
        "status": "research_only",
    }


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> Response:
    return JSONResponse({"status": "ok", "service": "tippmix-analyst-mcp"})


class BearerMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or scope["path"] == "/health":
            await self.app(scope, receive, send)
            return
        auth = dict(scope.get("headers", [])).get(b"authorization", b"").decode("utf-8", "replace")
        if TOKEN and hmac.compare_digest(auth, "Bearer " + TOKEN):
            await self.app(scope, receive, send)
            return
        resp = JSONResponse({"error": "Unauthorized"}, status_code=401)
        await resp(scope, receive, send)


def create_app():
    app = mcp.streamable_http_app()
    if TOKEN:
        app.add_middleware(BearerMiddleware)
    return app


app = create_app()
if __name__ == "__main__":
    import uvicorn
    if not TOKEN:
        print("WARNING: no bearer token (local development only)")
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
