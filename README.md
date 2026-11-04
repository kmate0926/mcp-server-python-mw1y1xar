# Tippmix Analyst MCP server — Render Free

## One-click Render Free deployment

[Deploy this Tippmix MCP server on Render Free](https://render.com/deploy?repo=https://github.com/kmate0926/mcp-server-python-mw1y1xar)

**Important:** Select the linked repository `kmate0926/mcp-server-python-mw1y1xar` and Free plan; review the new service before approving it. Do not deploy another Render-generated `mcp-server-python-*` repository. `MCP_API_TOKEN` is created as a secret by the Blueprint. The separate `OPENAI_API_KEY` and `OPENAI_MODEL` must be configured in Render Environment for model calls; do not commit credentials to GitHub.


This is a **research-only** MCP server for the six Tippmix Analyst sport modules. It is not a live Tippmix odds source, an automated bet placer, or an independent verification engine.

## Install on Render Free

If you already have a Render service, open **Settings → Build & Deploy** and make sure its connected repository is `kmate0926/mcp-server-python-mw1y1xar` with branch `main`. If not, connect this repository or create a new Free web service from it. Changing a different repository will not deploy this code.

- Runtime: Python
- Plan: Free
- Build command: `pip install -r requirements.txt`
- Start command: `python server.py`
- Health check path: `/health`
- MCP protocol URL after deploy: `https://YOUR-SERVICE.onrender.com/mcp`

In **Render → Environment**, set:
- `MCP_API_TOKEN`: long random secret; must be set in production (also supported by `render.yaml` blueprint).
- `OPENAI_API_KEY`: your **OpenAI API platform** key (not your ChatGPT subscription).
- `OPENAI_MODEL`: a model ID actually available to your API account.
- `PORT`: Render supplies it automatically; `10000` also works.

**Do not paste keys in chat or commit them to GitHub.**

## What is implemented

The MCP server exposes six independently callable functions:
`analyze_football`, `analyze_basketball`, `analyze_tennis`, `analyze_american_football`, `analyze_ice_hockey`, `analyze_handball`; and `get_capabilities`.

Each analysis tool expects one `markets_json` string containing `{"markets":[...]}`. Each market can have `sport`, `event_identifier`, `event`, `event_start_hu`, `market_exact`, `selection`, `official_odds`, `source`, `observed_at_hu`, and `evidence`. The server validates IDs and passes only supplied market information to a separate OpenAI Responses API call, then returns at most five **research-only** candidates. If the API key/model isn't configured, it returns `OPENAI_API_NOT_CONFIGURED`. It never fabricates verified odds or A-category picks.

## Verification procedure

1. Open `https://YOUR-SERVICE.onrender.com/health`; expect `{"status":"ok","service":"tippmix-analyst-mcp"}`.
2. Connect a compatible MCP client to `https://YOUR-SERVICE.onrender.com/mcp` using header `Authorization: Bearer YOUR_MCP_API_TOKEN`. Confirm `tools/list` returns the six analysis tools and `get_capabilities`.
3. Invoke `get_capabilities`. It must explicitly show `live_tippmix_odds_verified=false`.
4. Call `analyze_football` with `{"markets_json":"{\"markets\":[{\"sport\":\"football\",\"event_identifier\":\"DEMO-E1\",\"official_odds\":1.9,\"source\":\"SYNTHETIC_TEST_NOT_VERIFIED\"}]}"}`. The result is a research-only smoke test, NOT a betting suggestion.
5. Check Render **Events/Logs** for deployment success and any API errors.

**Important:** A green health check proves the process is running, not that AI calls or real Tippmix data retrieval works.

## Known limitations

- **No real-time classical Tippmix feed** is implemented. Provided odds are treated as user-supplied observations, not live verification.
- **No independent sports data retrieval, roster checking, or nine-gate A-grade scoring** is implemented.
- **Three verified Trixies require nine distinct, audited A-tier selections**; this server cannot guarantee or currently validate them.
- Render Free may spin down after inactivity, and OpenAI API charges are separate from Render.

The existing ChatGPT coordinator plugin needs a compatible connection to the running MCP endpoint. Its six skills alone do **not** call this server automatically.
