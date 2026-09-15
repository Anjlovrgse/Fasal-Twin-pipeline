"""
Fasal Twin - Government Scheme Advisor (Attached Decision Support)
Provides rule-based scheme matching and grounded retrieval explanations
for recommended logistics interventions.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

SCHEMES_DIR: Path = repo_root / "data" / "schemes"

# Mandatory verification notice (Non-negotiable requirement)
MANDATORY_KRISHI_BHAVAN_NOTICE: str = "Verify current eligibility with your local Krishi Bhavan."

SCHEME_METADATA: Dict[str, Dict[str, str]] = {
    "AIF": {
        "name": "Agriculture Infrastructure Fund (AIF)",
        "file": "aif_scheme.txt",
        "ministry": "Ministry of Agriculture & Farmers Welfare, Government of India",
    },
    "CGS_NPF": {
        "name": "Credit Guarantee Scheme for e-NWR-based Pledge Financing (CGS-NPF)",
        "file": "cgs_npf_scheme.txt",
        "ministry": "Warehousing Development and Regulatory Authority (WDRA) & DFPD",
    },
    "PMFBY": {
        "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
        "file": "pmfby_scheme.txt",
        "ministry": "Department of Agriculture & Farmers Welfare, GoI & Kerala Agri Dept",
    },
    "SUPPLYCO_PROCUREMENT": {
        "name": "Kerala Supplyco Paddy Procurement & State Incentive Bonus Scheme",
        "file": "supplyco_procurement_scheme.txt",
        "ministry": "Department of Food and Civil Supplies, Government of Kerala",
    },
}

# Rule-based dispatch table mapping action types to scheme candidates
ACTION_SCHEME_RULES: Dict[str, List[str]] = {
    "staggered_holding": ["AIF", "CGS_NPF"],
    "redirect_mandi": ["SUPPLYCO_PROCUREMENT", "AIF"],
    "direct_mill_offload": ["SUPPLYCO_PROCUREMENT", "AIF"],
    "weather_risk_flagged": ["PMFBY"],
    "weather_shifted": ["PMFBY", "SUPPLYCO_PROCUREMENT"],
    "do_nothing": ["SUPPLYCO_PROCUREMENT"],
}


class SchemeAdvisor:
    """
    RAG-based Government Scheme Advisor attached strictly to recommendation action types.
    """

    def __init__(self, schemes_dir: Optional[Path] = None):
        self.schemes_dir = schemes_dir or SCHEMES_DIR

    def match_scheme(self, action_type: str) -> List[str]:
        """
        Rule-based matching from action type to applicable scheme candidate IDs.
        """
        norm_action = action_type.lower().strip()
        matched = ACTION_SCHEME_RULES.get(norm_action)
        if not matched:
            # Substring matching for flexible action type strings
            if "hold" in norm_action or "stagger" in norm_action or "store" in norm_action:
                return ["AIF", "CGS_NPF"]
            elif "weather" in norm_action or "rain" in norm_action:
                return ["PMFBY"]
            elif "mill" in norm_action or "divert" in norm_action or "redirect" in norm_action:
                return ["SUPPLYCO_PROCUREMENT", "AIF"]
            else:
                return ["SUPPLYCO_PROCUREMENT"]
        return matched

    def _read_and_chunk_scheme_document(self, filename: str) -> List[Dict[str, str]]:
        """Reads scheme document and splits into semantic paragraph chunks."""
        filepath = self.schemes_dir / filename
        if not filepath.exists():
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        raw_paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        chunks = []
        doc_header = raw_paragraphs[0] if raw_paragraphs else "Unknown Document"

        for idx, p in enumerate(raw_paragraphs):
            chunks.append({
                "chunk_id": f"{filename}#p{idx}",
                "doc_title": doc_header.replace("#", "").strip(),
                "text": p,
            })
        return chunks

    def get_scheme_explanation(self, scheme_id: str, action_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves relevant paragraphs from the scheme document and generates
        a grounded summary with the mandatory Krishi Bhavan verification notice.
        """
        meta = SCHEME_METADATA.get(scheme_id.upper())
        if not meta:
            return {
                "scheme_id": scheme_id,
                "status": "scheme_not_found",
                "scheme_name": scheme_id,
                "summary": f"Scheme '{scheme_id}' is not in the active registry.",
                "mandatory_notice": MANDATORY_KRISHI_BHAVAN_NOTICE,
            }

        chunks = self._read_and_chunk_scheme_document(meta["file"])
        if not chunks:
            return {
                "scheme_id": scheme_id,
                "status": "document_missing",
                "scheme_name": meta["name"],
                "source_document": meta["file"],
                "summary": f"Scheme source document '{meta['file']}' is currently unavailable in data/schemes/.",
                "mandatory_notice": MANDATORY_KRISHI_BHAVAN_NOTICE,
                "phrasing_source": "template",
            }

        source_citation = chunks[0]["text"] if chunks else meta["name"]
        extracted_facts = [c["text"] for c in chunks[1:4]] if len(chunks) > 1 else [c["text"] for c in chunks]

        # Plain language summary grounded strictly in document chunks (use LLM if available)
        from src.llm_client import get_llm_client
        client = get_llm_client()
        llm_resp = client.generate_grounded_text(
            facts=[{"fact": f} for f in extracted_facts],
            instruction="Summarize the scheme in plain language using the provided facts."
        )
        summary = llm_resp["text"]
        phrasing_source = llm_resp["phrasing_source"]

        return {
            "scheme_id": scheme_id,
            "scheme_name": meta["name"],
            "ministry": meta["ministry"],
            "matched_action_type": action_type,
            "source_document": meta["file"],
            "plain_language_summary": summary,
            "grounded_clauses": extracted_facts,
            "mandatory_notice": MANDATORY_KRISHI_BHAVAN_NOTICE,
            "phrasing_source": phrasing_source,
        }

    def advise_for_recommendation(self, action_type: str) -> Dict[str, Any]:
        """
        Full advisor pipeline for a recommendation action type.
        """
        matched_ids = self.match_scheme(action_type)
        explanations = [self.get_scheme_explanation(sid, action_type) for sid in matched_ids]

        return {
            "action_type": action_type,
            "matched_schemes_count": len(matched_ids),
            "matched_scheme_ids": matched_ids,
            "schemes": explanations,
            "mandatory_notice": MANDATORY_KRISHI_BHAVAN_NOTICE,
        }


if __name__ == "__main__":
    advisor = SchemeAdvisor()
    advice = advisor.advise_for_recommendation("staggered_holding")
    print("\n" + "=" * 80)
    print(" GOVERNMENT SCHEME ADVISOR")
    print("=" * 80)
    print(f"Action Type: {advice['action_type']}")
    print(f"Matched Schemes: {advice['matched_scheme_ids']}")
    for s in advice["schemes"]:
        print(f"\nScheme: {s['scheme_name']}")
        print(f"  Summary: {s['plain_language_summary']}")
        print(f"  Notice:  {s['mandatory_notice']}")
    print("=" * 80 + "\n")
