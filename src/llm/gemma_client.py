"""
Gemma LLM Client using the official Ollama Python library.
Provides robust connection management, timeout controls, retry with exponential backoff,
and strict JSON extraction and validation for gemma4:31b-cloud.
"""

from typing import Dict, Any, Optional, List, Union
import json
import re
import time
import logging
import ollama
from pydantic import BaseModel

from src.config import (
    DEFAULT_OLLAMA_MODEL,
    OLLAMA_HOST,
    OLLAMA_TIMEOUT,
    OLLAMA_MAX_RETRIES,
)

logger = logging.getLogger(__name__)


class GemmaClientError(Exception):
    """Base exception for Gemma client errors."""
    pass


class GemmaConnectionError(GemmaClientError):
    """Raised when unable to connect to Ollama service or cloud."""
    pass


class GemmaTimeoutError(GemmaClientError):
    """Raised when an Ollama request times out."""
    pass


class GemmaJSONParseError(GemmaClientError):
    """Raised when Gemma response fails JSON decoding after sanitization."""
    def __init__(self, message: str, raw_content: str):
        super().__init__(message)
        self.raw_content = raw_content


class GemmaClient:
    """
    Client for interfacing with Gemma 4 31B Cloud via Ollama.
    Enforces structured JSON generation, automatic markdown fence stripping,
    and resilient error handling.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        host: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self.model = model or DEFAULT_OLLAMA_MODEL
        self.host = host or OLLAMA_HOST
        self.timeout = timeout if timeout is not None else OLLAMA_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else OLLAMA_MAX_RETRIES

        # Initialize Ollama Client
        self._client = ollama.Client(host=self.host)

    def check_health(self) -> Dict[str, Any]:
        """
        Pings Ollama and tests model connectivity with a minimal prompt.
        """
        start = time.time()
        try:
            response = self._client.chat(
                model=self.model,
                messages=[{"role": "user", "content": "Ping. Respond strictly with 'PONG'."}],
            )
            elapsed = time.time() - start
            content = response.get("message", {}).get("content", "").strip()
            return {
                "status": "healthy",
                "model": self.model,
                "latency_seconds": round(elapsed, 2),
                "reply": content,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "model": self.model,
                "error": str(e),
            }

    @staticmethod
    def extract_json_from_text(text: str) -> Dict[str, Any]:
        """
        Extracts and parses JSON object from a string that may contain
        markdown code fences (```json ... ```) or conversational commentary.
        """
        cleaned = text.strip()

        # Remove markdown code fence if present
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            # drop first line (e.g. ```json or ```)
            if len(lines) >= 2:
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()

        # Direct attempt
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Substring extraction: find outermost curly braces
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            candidate = cleaned[start_idx:end_idx + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError as err:
                raise GemmaJSONParseError(
                    f"Failed to parse extracted JSON substring: {err}",
                    raw_content=text
                )

        raise GemmaJSONParseError("No JSON object found in response.", raw_content=text)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
    ) -> str:
        """
        Generates free-text response with retries.
        """
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        last_err: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug("Ollama request attempt %d for model %s", attempt, self.model)
                response = self._client.chat(
                    model=self.model,
                    messages=messages,
                    options={"temperature": temperature},
                )
                return response.get("message", {}).get("content", "")
            except Exception as e:
                last_err = e
                logger.warning("Ollama call failed on attempt %d: %s", attempt, e)
                if attempt < self.max_retries:
                    time.sleep(1.0 * (2 ** (attempt - 1)))  # Exponential backoff

        raise GemmaConnectionError(
            f"Failed to connect to Ollama model '{self.model}' after {self.max_retries} attempts: {last_err}"
        )

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[type[BaseModel]] = None,
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Generates structured JSON using Ollama format="json" and parses the result.
        Validates against Pydantic schema if provided.
        """
        # Inject schema or JSON formatting requirement into prompt if needed
        if schema is not None:
            schema_json = json.dumps(schema.model_json_schema(), indent=2)
            effective_prompt = (
                f"{prompt}\n\n"
                f"CRITICAL: You must return ONLY a valid JSON object matching this schema:\n"
                f"{schema_json}\n"
                f"Do NOT output conversational commentary, notes, or explanations outside the JSON."
            )
        elif "json" not in prompt.lower():
            effective_prompt = (
                f"{prompt}\n\n"
                f"CRITICAL: Return ONLY a valid JSON object. Do not include any conversational text."
            )
        else:
            effective_prompt = prompt

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": effective_prompt})

        last_err: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.chat(
                    model=self.model,
                    messages=messages,
                    format="json",
                    options={"temperature": temperature},
                )
                raw_text = response.get("message", {}).get("content", "")
                parsed_json = self.extract_json_from_text(raw_text)

                if schema is not None:
                    # Validate through Pydantic
                    validated = schema.model_validate(parsed_json)
                    return validated.model_dump()

                return parsed_json

            except GemmaJSONParseError as jpe:
                logger.warning("JSON parse error on attempt %d: %s", attempt, jpe)
                last_err = jpe
                if attempt < self.max_retries:
                    time.sleep(1.0)
            except Exception as e:
                logger.warning("Ollama connection error on attempt %d: %s", attempt, e)
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(1.0 * (2 ** (attempt - 1)))

        raise GemmaClientError(
            f"Failed to generate valid JSON from '{self.model}' after {self.max_retries} attempts: {last_err}"
        )


def get_gemma_client() -> GemmaClient:
    """Returns standard GemmaClient instance."""
    return GemmaClient()
