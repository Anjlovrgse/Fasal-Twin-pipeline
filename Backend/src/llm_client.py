from __future__ import annotations
"""src/llm_client.py"""
"""Gemini LLM client wrapper with hallucination guardrails.

Provides a single function `generate_grounded_text` that takes a list of fact
objects (each a dict with arbitrary keys, but typically containing a 'fact'
string) and an instruction. The function calls the Google Gemini model via
`google-generativeai`. It validates that any numeric tokens in the model output
are present in the supplied facts; if a fabricated numeric token is detected it
falls back to a simple template‑concatenation approach.

The wrapper also returns a ``phrasing_source`` field indicating whether the
output came from the LLM ('llm') or the fallback ('template').
"""

import re
import logging
from typing import List, Dict, Any, Optional

from google import genai
# Types are accessed via genai.types in the new SDK
types = genai.types

from src.config import get_settings, ConfigurationError

_logger = logging.getLogger(__name__)

class GeminiClient:
    """Singleton‑style client for the Gemini model.

    The client is lazily initialised; the API key is read from the settings
    only when a generation request is made. A ``ConfigurationError`` is raised
    if the key is missing at call time.
    """

    _instance: Optional["GeminiClient"] = None
    _model_name: str = "gemini-1.5-pro"

    def __new__(cls) -> "GeminiClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._api_key: Optional[str] = None
        self._initialized = True

    def _ensure_key(self) -> str:
        if self._api_key:
            return self._api_key
        settings = get_settings()
        if not settings.gemini_api_key:
            # Log warning and use a dummy key to allow fallback path without raising error.
            _logger.warning("GEMINI_API_KEY not set; proceeding with fallback generation.")
            # Use a placeholder API key; the Gemini client will not be called if generation fails.
            self._api_key = "DUMMY_KEY"
        else:
            self._api_key = settings.gemini_api_key
        return self._api_key

    def _extract_numeric_tokens(self, text: str) -> List[str]:
        return re.findall(r"\d+(?:\.\d+)?", text)

    def _detect_fabricated_numbers(self, output_nums: List[str], fact_texts: List[str]) -> bool:
        combined = " ".join(fact_texts)
        for num in output_nums:
            if num not in combined:
                return True
        return False

    def generate_grounded_text(
        self,
        facts: List[Dict[str, Any]],
        instruction: str,
        timeout_seconds: int = 20,
    ) -> Dict[str, Any]:
        """Generate a grounded textual response.

        Returns a dict with ``text`` and ``phrasing_source`` ("llm" or "template").
        """
        # Build prompt with numbered facts.
        fact_lines = []
        for idx, f in enumerate(facts, start=1):
            fact_lines.append(f"{idx}. {f.get('fact', str(f))}")
        prompt = f"Instruction: {instruction}\n\nFacts:\n" + "\n".join(fact_lines)

        # Ensure API key.
        # Ensure API key (client reads env automatically)
        # Ensure we have a real API key before contacting Gemini.
        api_key = self._ensure_key()
        if api_key == "DUMMY_KEY":
            # No real key – skip LLM call and use fallback/template.
            generated = ""
        else:
            client = genai.Client()
            try:
                response = client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(max_output_tokens=1024, temperature=0.2),
                    request_options=types.RequestOptions(timeout=timeout_seconds),
                )
                generated = response.text.strip()
            except Exception as exc:
                _logger.warning("Gemini generation failed: %s", exc)
                generated = ""



        # Guard‑rail for fabricated numbers.
        output_nums = self._extract_numeric_tokens(generated)
        fact_texts = [str(f.get('fact', '')) for f in facts]
        fabricated = self._detect_fabricated_numbers(output_nums, fact_texts)

        if fabricated or not generated:
            fallback = instruction
            if fact_lines:
                fallback += " Facts: " + ", ".join(fact_lines)
            generated = fallback
            source = "template"
        else:
            source = "llm"

        return {"text": generated, "phrasing_source": source}

def get_llm_client() -> GeminiClient:
    """Accessor used by other modules."""
    return GeminiClient()
