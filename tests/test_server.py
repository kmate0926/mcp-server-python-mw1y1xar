"""Offline smoke checks: no external API calls, no betting recommendation."""
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

def test_import_and_configuration(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    import server
    c = server.get_capabilities()
    assert len(c["sports"]) == 6
    assert not c["model_configured"]
    assert c["live_tippmix_odds_verified"] is False

def test_missing_api_does_not_fabricate(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    import server
    entry = {"sport": "football", "event_identifier": "DEMO-ONLY",
             "official_odds": 2.0, "source": "SYNTHETIC_NOT_VERIFIED"}
    res = server.analyze("football", json.dumps({"markets": [entry]}))
    assert res["error"] == "OPENAI_API_NOT_CONFIGURED"
    assert res["candidates"] == []
    assert res["verification"] == "RESEARCH_ONLY_NOT_INDEPENDENTLY_VERIFIED"

def test_invalid_input_fails_closed():
    import server
    for inp in ("not json", "{}", '{"markets": 4}', '{"markets": [{}]}'):
        res = server.analyze("football", inp)
        assert res["candidates"] == []
        assert res["error"] in ("INVALID_INPUT_MARKETS_JSON", None)
