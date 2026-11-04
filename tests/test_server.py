"""Offline unit checks. Live MCP protocol checks require dependencies and deployment."""
import ast
import pathlib

CODE = pathlib.Path(__file__).resolve().parents[1].joinpath("server.py").read_text()

def test_parse():
    ast.parse(CODE)

def test_six_separate_tools():
    for name in ["analyze_football","analyze_basketball","analyze_tennis","analyze_american_football","analyze_ice_hockey","analyze_handball"]:
        assert "def " + name + "(" in CODE

def test_research_only():
    assert "st_tier=\"KUTATASI\"" in CODE
    assert '"live_tippmix_odds_verified": False' in CODE
    assert "MCP_API_TOKEN" in CODE
