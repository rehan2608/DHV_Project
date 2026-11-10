"""
Unit tests for GemmaClient.
"""

import pytest
from pydantic import BaseModel, Field
from src.llm.gemma_client import (
    GemmaClient,
    GemmaJSONParseError,
    get_gemma_client,
)


def test_extract_json_clean():
    raw = '{"operation": "rank", "limit": 10}'
    parsed = GemmaClient.extract_json_from_text(raw)
    assert parsed == {"operation": "rank", "limit": 10}


def test_extract_json_markdown_wrapped():
    raw = """```json
{
    "category": "Engineering",
    "years": [2020, 2025]
}
```"""
    parsed = GemmaClient.extract_json_from_text(raw)
    assert parsed["category"] == "Engineering"
    assert parsed["years"] == [2020, 2025]


def test_extract_json_noisy_text():
    raw = """Here is the analytical plan you requested:
{
    "intent": "compare",
    "entities": ["IIT Bombay", "IIT Madras"]
}
Hope this helps!"""
    parsed = GemmaClient.extract_json_from_text(raw)
    assert parsed["intent"] == "compare"
    assert "IIT Madras" in parsed["entities"]


def test_extract_json_invalid_raises():
    raw = "No json here at all!"
    with pytest.raises(GemmaJSONParseError):
        GemmaClient.extract_json_from_text(raw)


@pytest.mark.live_ollama
def test_gemma_health_check():
    client = get_gemma_client()
    health = client.check_health()
    assert health["status"] == "healthy"
    assert health["model"] == "gemma4:31b-cloud"


@pytest.mark.live_ollama
def test_gemma_structured_json_generation():
    class TestPlan(BaseModel):
        intent: str = Field(description="Query intent")
        metric: str = Field(description="Target metric")

    client = get_gemma_client()
    prompt = "Categorize the question 'Compare research performance of IITs' into intent and metric."
    result = client.generate_json(prompt, schema=TestPlan)
    assert "intent" in result
    assert "metric" in result

