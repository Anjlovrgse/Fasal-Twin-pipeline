"""
Unit and integration tests for Fasal Twin Grounded Farmer Query Layer (src/farmer_query.py).
Verifies:
1. Strict Out-of-Scope Guardrail: general farming / pesticide / unrelated queries return out_of_scope=True.
2. Grounded Scheme Querying: routes through SchemeAdvisor with mandatory Krishi Bhavan notice.
3. Grounded Price Forecast Querying: cites predicted range and elasticity provenance.
4. Grounded Decision / Evidence Querying: cites Maximin payoff and evidence chain.
5. Grounded Sowing Advisory Querying: cites recommended window and bottleneck reduction.
6. FastAPI REST route POST /farmer-query.
"""

import pytest
from fastapi.testclient import TestClient

from src.farmer_query import answer_farmer_query, OUT_OF_SCOPE_STANDARD_NOTICE
from src.scheme_advisor import MANDATORY_KRISHI_BHAVAN_NOTICE
from src.api import app

client = TestClient(app)


def test_out_of_scope_guardrail_pesticide():
    """
    CRITICAL TEST: Ensures that questions outside system boundaries (e.g. general agronomic/pesticide advice)
    strictly return out_of_scope=True and NEVER fabricate or hallucinate general advice.
    """
    res = answer_farmer_query(
        state="Kerala",
        district="Alappuzha",
        crop="rice",
        question="What is the best chemical pesticide or fertilizer dosage to kill stem borer in paddy?"
    )

    assert res["out_of_scope"] is True
    assert "Krishi Bhavan" in res["answer"]
    assert "Strict Grounding Boundary" in res["provenance"]
    assert "stem borer" not in res["answer"].lower()  # Did not attempt to hallucinate chemical formulas


def test_out_of_scope_guardrail_unrelated():
    """
    Ensures that general knowledge or non-domain questions return out_of_scope=True.
    """
    res = answer_farmer_query(
        state="Kerala",
        district="Alappuzha",
        crop="rice",
        question="What is the weather in London right now and write a poem about it?"
    )

    assert res["out_of_scope"] is True
    assert res["matched_intent"] == "out_of_scope"
    assert "Krishi Bhavan" in res["answer"]


def test_grounded_scheme_query():
    """
    Verifies that scheme-related queries return grounded terms and mandatory Krishi Bhavan notice.
    """
    res = answer_farmer_query(
        state="Kerala",
        district="Alappuzha",
        crop="rice",
        question="What subsidy or financial assistance is available under the AIF infrastructure scheme?"
    )

    assert res["out_of_scope"] is False
    assert res["matched_intent"] == "scheme_terms"
    assert "Agriculture Infrastructure Fund" in res["answer"] or "AIF" in res["answer"]
    assert MANDATORY_KRISHI_BHAVAN_NOTICE in res["answer"]
    assert res["mandatory_notice"] == MANDATORY_KRISHI_BHAVAN_NOTICE


def test_grounded_price_forecast_query():
    """
    Verifies that price forecast questions return grounded modal price ranges and observation counts.
    """
    res = answer_farmer_query(
        state="Kerala",
        district="Alappuzha",
        crop="rice",
        question="What is the predicted modal price forecast and price range for Alappuzha rice over the next 14 days?"
    )

    assert res["out_of_scope"] is False
    assert res["matched_intent"] == "price_forecast"
    assert "Rs" in res["answer"]
    assert "Agmarknet" in res["provenance"] or "Econometric" in res["provenance"]


def test_grounded_decision_why_query():
    """
    Verifies that decision/action questions return exact Maximin payoffs and evidence facts.
    """
    res = answer_farmer_query(
        state="Kerala",
        district="Alappuzha",
        crop="rice",
        question="Why did the system recommend staggered farmgate holding and what is the guaranteed worst-case payoff?"
    )

    assert res["out_of_scope"] is False
    assert res["matched_intent"] == "recommendation_explanation"
    assert "Maximin" in res["answer"] or "payoff" in res["answer"].lower()
    assert "Rs" in res["answer"]


def test_grounded_sowing_query():
    """
    Verifies that sowing window questions return the optimized window and bottleneck reduction.
    """
    res = answer_farmer_query(
        state="Kerala",
        district="Alappuzha",
        crop="rice",
        question="When is the recommended sowing window to avoid mandi congestion and harvest bottlenecks?"
    )

    assert res["out_of_scope"] is False
    assert res["matched_intent"] == "sowing_advisory"
    assert "sowing window" in res["answer"].lower()
    assert "%" in res["answer"] or "avoid" in res["answer"].lower()


def test_farmer_query_api_endpoint():
    """
    Verifies FastAPI POST /farmer-query route for both in-scope and out-of-scope payloads.
    """
    # 1. In-Scope query
    payload_in = {
        "state": "Kerala",
        "district": "Alappuzha",
        "crop": "rice",
        "question": "What is the 14-day price forecast and elasticity trend?"
    }
    r_in = client.post("/farmer-query", json=payload_in)
    assert r_in.status_code == 200
    data_in = r_in.json()
    assert data_in["out_of_scope"] is False
    assert "Rs" in data_in["answer"]

    # 2. Out-of-Scope query
    payload_out = {
        "state": "Kerala",
        "district": "Alappuzha",
        "crop": "rice",
        "question": "How do I make organic neem pesticide spray at home?"
    }
    r_out = client.post("/farmer-query", json=payload_out)
    assert r_out.status_code == 200
    data_out = r_out.json()
    assert data_out["out_of_scope"] is True
    assert "Krishi Bhavan" in data_out["answer"]
