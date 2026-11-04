"""Offline checks: no external APIs and no paid model calls in free mode."""
import ast
import json
import pathlib

CODE = pathlib.Path(__file__).resolve().parents[1].joinpath("server.py").read_text()

def test_python_syntax():
    ast.parse(CODE)

def test_six_tools_declared():
    for name in ("analyze_football", "analyze_basketball", "analyze_tennis",
                 "analyze_american_football", "analyze_ice_hockey", "analyze_handball"):
        assert "def " + name + "(" in CODE

def test_free_mode_cannot_trigger_api_even_if_key_present(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-not-real-key")
    monkeypatch.setenv("OPENAI_MODEL", "fake-test-model")
    import server
    assert server.FREE_ONLY_MODE is True
    caps = server.get_capabilities()
    assert caps["free_only_mode"] is True
    assert caps["external_ai_api_calls_enabled"] is False
    assert caps["live_tippmix_odds_verified"] is False

def test_six_sports_research_only(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-not-real-key")
    monkeypatch.setenv("OPENAI_MODEL", "fake-test-model")
    import server
    for sport in server.SPORTS:
        markets = [
            {"sport": sport, "event_identifier": sport+"-demo", "event": "Synthetic test",
             "official_odds": 1.95, "source": "SYNTHETIC_NOT_VERIFIED"},
            {"sport": sport, "event_identifier": sport+"-low", "event": "Synthetic test",
             "official_odds": 1.55, "source": "SYNTHETIC_NOT_VERIFIED"},
        ]
        res = server.analyze(sport, json.dumps({"markets": markets}))
        assert res["error"] is None
        assert res["execution"] == "deterministic_free_only_no_api"
        assert len(res["candidates"]) == 1
        assert res["candidates"][0]["status"] == "NEM_HITELESITETT"
        assert res["candidates"][0]["st_score"] is None
        assert res["candidates"][0]["event_identifier"] == sport+"-demo"

def test_invalid_input_fails_closed():
    import server
    for inp in ("not json", "{}", '{"markets": 4}'):
        res = server.analyze("football", inp)
        assert res["candidates"] == []
        assert res["error"] == "INVALID_INPUT_MARKETS_JSON"

def test_empty_and_ineligible_cases():
    import server
    for inp in ('{"markets": []}', '{"markets":[{"event_identifier":"low","official_odds":1.79}]}'):
        res = server.analyze("football", inp)
        assert res["candidates"] == []
