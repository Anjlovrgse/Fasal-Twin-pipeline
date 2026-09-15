"""
Unit tests for scheme_advisor.py verifying rule-based matching, grounded retrieval, and Krishi Bhavan notice.
"""

import sys
from pathlib import Path
import pytest

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from src.scheme_advisor import SchemeAdvisor, MANDATORY_KRISHI_BHAVAN_NOTICE


def test_scheme_matching_rules():
    """Verifies that action types map to correct scheme candidate IDs."""
    advisor = SchemeAdvisor()

    # Store / holding action -> AIF & CGS-NPF
    matched_holding = advisor.match_scheme("staggered_holding")
    assert "AIF" in matched_holding
    assert "CGS_NPF" in matched_holding

    # Weather action -> PMFBY
    matched_weather = advisor.match_scheme("weather_risk_flagged")
    assert "PMFBY" in matched_weather


def test_scheme_explanation_contains_mandatory_notice():
    """
    Verifies that all retrieved scheme explanations include the Krishi Bhavan notice
    and authentic source document references.
    """
    advisor = SchemeAdvisor()
    advice = advisor.advise_for_recommendation("staggered_holding")

    assert advice["matched_schemes_count"] >= 2
    for s in advice["schemes"]:
        assert s["mandatory_notice"] == MANDATORY_KRISHI_BHAVAN_NOTICE
        assert "Krishi Bhavan" in s["mandatory_notice"]
        assert len(s["plain_language_summary"]) > 20
        assert s["source_document"].endswith(".txt")
