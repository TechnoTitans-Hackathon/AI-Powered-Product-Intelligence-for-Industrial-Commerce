"""AI Provider interface and implementations."""

from __future__ import annotations

import json
import os
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from ai_engine.schemas import (
    DiscoveryResult,
    FieldValue,
    ProductIdentity,
    ProductInput,
    FieldStatus,
    SourceType,
)

logger = logging.getLogger(__name__)

def is_transient_error(e: Exception) -> bool:
    """Determine if an error is transient. Do NOT retry on 404s, Timeouts, or Auth errors."""
    error_str = str(e).lower()
    # Do not retry on Not Found errors (e.g., model missing)
    if "404" in error_str or "not found" in error_str:
        return False
    # Do not retry on timeouts (since our timeout is already generous)
    if "timeout" in error_str or "readtimeout" in error_str:
        return False
    # Do not retry on authentication errors
    if "401" in error_str or "403" in error_str or "unauthorized" in error_str:
        return False
    return True


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class AIProviderInterface(ABC):
    """Abstract interface for AI model providers.

    The core agents depend on this interface, not on any specific provider.
    """

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        system_instruction: str = "",
        response_schema: Optional[dict] = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Generate a structured JSON response from the model."""
        ...

    @abstractmethod
    async def analyze_multimodal(
        self,
        prompt: str,
        image_paths: list[str] = None,
        audio_paths: list[str] = None,
        video_paths: list[str] = None,
        system_instruction: str = "",
        response_schema: Optional[dict] = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Generate a structured response using multimodal inputs (images/audio/video)."""
        ...

    @abstractmethod
    async def analyze_product(
        self,
        product_info: dict[str, Any],
        task: str,
        context: str = "",
    ) -> dict[str, Any]:
        """Analyze product information for a specific task."""
        ...

    @abstractmethod
    async def extract_attributes(
        self,
        product_info: dict[str, Any],
        evidence_texts: list[str],
        required_attributes: list[str],
    ) -> list[dict[str, Any]]:
        """Extract structured attributes from evidence."""
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this provider."""
        ...


# ---------------------------------------------------------------------------
# Gemini Provider (real)
# ---------------------------------------------------------------------------

class GeminiProvider(AIProviderInterface):
    """Real Gemini API provider using google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "google-genai package required. Install with: pip install google-genai"
                )
        return self._client

    @retry(stop=stop_after_attempt(7), wait=wait_exponential(min=2, max=30))
    async def generate_structured(
        self,
        prompt: str,
        system_instruction: str = "",
        response_schema: Optional[dict] = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        import time
        time.sleep(10) # Throttle to max 6 RPM

        client = self._get_client()
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
        )
        if system_instruction:
            config.system_instruction = system_instruction

        full_prompt = prompt
        if response_schema:
            full_prompt += f"\n\nRespond with valid JSON matching this schema:\n{json.dumps(response_schema, indent=2)}"

        response = client.models.generate_content(
            model=self.model_name,
            contents=full_prompt,
            config=config,
        )

        return self._parse_json_response(response.text)

    @retry(stop=stop_after_attempt(7), wait=wait_exponential(min=2, max=30))
    async def analyze_multimodal(
        self,
        prompt: str,
        image_paths: list[str] = None,
        audio_paths: list[str] = None,
        video_paths: list[str] = None,
        system_instruction: str = "",
        response_schema: Optional[dict] = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        import time
        time.sleep(10)

        client = self._get_client()
        from google.genai import types
        from PIL import Image

        config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
        )
        if system_instruction:
            config.system_instruction = system_instruction

        full_prompt = prompt
        if response_schema:
            full_prompt += f"\n\nRespond with valid JSON matching this schema:\n{json.dumps(response_schema, indent=2)}"

        contents = []
        if image_paths:
            for p in image_paths:
                contents.append(Image.open(p))
        contents.append(full_prompt)

        response = client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config,
        )

        return self._parse_json_response(response.text)

    @retry(stop=stop_after_attempt(7), wait=wait_exponential(min=2, max=30))
    async def analyze_product(
        self,
        product_info: dict[str, Any],
        task: str,
        context: str = "",
    ) -> dict[str, Any]:
        import time
        time.sleep(4) # Throttle to max 15 RPM

        client = self._get_client()
        from google.genai import types

        prompt = f"""Task: {task}

Product Information:
{json.dumps(product_info, indent=2, default=str)}

{f'Additional Context: {context}' if context else ''}

Respond with valid JSON."""

        config = types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            system_instruction="You are an expert product data analyst. Analyze product information accurately. Never fabricate specifications or evidence. If information is not available, mark it as missing.",
        )

        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        return self._parse_json_response(response.text)

    @retry(stop=stop_after_attempt(7), wait=wait_exponential(min=2, max=30))
    async def extract_attributes(
        self,
        product_info: dict[str, Any],
        evidence_texts: list[str],
        required_attributes: list[str],
    ) -> list[dict[str, Any]]:
        client = self._get_client()
        from google.genai import types

        evidence_block = "\n---\n".join(evidence_texts[:5])  # Context control

        prompt = f"""Extract product attributes from the provided evidence.

Product: {json.dumps(product_info, indent=2, default=str)}

Evidence:
{evidence_block}

Required Attributes: {json.dumps(required_attributes)}

For each attribute, return:
- "attribute": the attribute name
- "value": extracted value or null if not found
- "unit": unit of measurement if applicable
- "status": "DIRECTLY_SUPPORTED" if directly stated, "INFERRED" if inferred, "MISSING" if not found
- "evidence_snippet": the exact text that supports this value
- "source": which evidence source this came from
- "confidence": 0.0-1.0

CRITICAL RULES:
- NEVER invent values not supported by evidence
- Mark as MISSING if not found
- Mark as INFERRED if deduced but not directly stated
- Include the exact evidence snippet that supports each value

Respond with a JSON array of attribute objects."""

        config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            system_instruction="You are a precise product data extraction engine. Extract only what is directly supported by evidence. Never fabricate data.",
        )

        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        result = self._parse_json_response(response.text)
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "attributes" in result:
            return result["attributes"]
        return [result] if isinstance(result, dict) else []

    def get_provider_name(self) -> str:
        return f"Gemini ({self.model_name})"

    @staticmethod
    def _parse_json_response(text: str) -> Any:
        """Parse JSON from AI response with controlled repair."""
        text = text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Attempt controlled repair: find first { or [ and last } or ]
            start_obj = text.find("{")
            start_arr = text.find("[")
            if start_obj == -1 and start_arr == -1:
                raise ValueError(f"Cannot parse AI response as JSON: {text[:200]}")

            if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
                end = text.rfind("]")
                if end != -1:
                    try:
                        return json.loads(text[start_arr : end + 1])
                    except json.JSONDecodeError:
                        pass

            if start_obj != -1:
                end = text.rfind("}")
                if end != -1:
                    try:
                        return json.loads(text[start_obj : end + 1])
                    except json.JSONDecodeError:
                        pass

            raise ValueError(f"Cannot parse AI response as JSON after repair: {text[:200]}")


# ---------------------------------------------------------------------------
# Ollama Provider (Local LLM)
# ---------------------------------------------------------------------------

class OllamaProvider(AIProviderInterface):
    """Local Qwen3.5 LLM provider via Ollama."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None, timeout: int = 1200):
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.model_name = model or os.environ.get("OLLAMA_MODEL", "qwen3.5:9b-q4_K_M")
        default_timeout = int(os.environ.get("PROVIDER_TIMEOUT_SECONDS", timeout))
        self.timeout = int(os.environ.get("OLLAMA_TIMEOUT_SECONDS", os.environ.get("OLLAMA_TIMEOUT", default_timeout)))
        self._client = None

    def _get_client(self):
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    @retry(retry=retry_if_exception(is_transient_error), stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def generate_structured(
        self,
        prompt: str,
        system_instruction: str = "",
        response_schema: Optional[dict] = None,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        client = self._get_client()

        # Build prompt enforcing JSON structure
        full_prompt = prompt
        if response_schema:
            full_prompt += f"\n\nOutput STRICT valid JSON matching this schema. NO markdown, NO text, JUST JSON:\n{json.dumps(response_schema, indent=2)}"
        else:
            full_prompt += "\n\nOutput STRICT valid JSON. NO markdown, NO text, JUST JSON."

        # Prevent think-block interference with JSON output
        sys_msg = system_instruction if system_instruction else "You are a helpful assistant that outputs valid JSON."
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": full_prompt},
            ],
            "stream": False,
            "options": {
                "num_ctx": int(os.environ.get("OLLAMA_NUM_CTX", "2048")),
                "num_predict": 2048,
                "temperature": temperature,
            }
        }

        try:
            logger.info(f"\n[DIAGNOSTIC] Ollama POST /api/chat | Provider: OLLAMA | Model: {self.model_name} | URL: {self.base_url}")
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            message = data.get("message", {})
            content = message.get("content", "")
            if not content.strip():
                content = message.get("thinking", "")

            return self._parse_json_response(content)
        except Exception as e:
            logger.error(f"OllamaProvider generate_structured failed: {e}")
            raise RuntimeError(f"OllamaProvider generation failed: {e}")

    @retry(retry=retry_if_exception(is_transient_error), stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def analyze_multimodal(
        self,
        prompt: str,
        image_paths: list[str] = None,
        audio_paths: list[str] = None,
        video_paths: list[str] = None,
        system_instruction: str = "",
        response_schema: Optional[dict] = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Ollama local text-only model fallback for multimodal requests."""
        if response_schema:
            logger.warning(f"Ollama text-only provider received multimodal request. Attempting graceful fallback.")
            # We don't have vision, return empty/missing placeholders matching schema
            fallback = {}
            for key in response_schema.get("properties", {}).keys():
                if response_schema["properties"][key].get("type") == "array":
                    fallback[key] = []
                elif response_schema["properties"][key].get("type") == "string":
                    fallback[key] = "Vision analysis unavailable in LOCAL mode"
                else:
                    fallback[key] = None
            return fallback
        return {"error": "Vision analysis unavailable in LOCAL mode"}

    @retry(retry=retry_if_exception(is_transient_error), stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def analyze_product(
        self,
        product_info: dict[str, Any],
        task: str,
        context: str = "",
    ) -> dict[str, Any]:
        client = self._get_client()

        prompt = f"Task: {task}\n\nProduct Information:\n{json.dumps(product_info, indent=2, default=str)}\n\n"
        if context:
            prompt += f"Additional Context: {context}\n\n"

        prompt += "Respond with strictly valid JSON matching the exact requested keys. No surrounding text, no markdown."

        system_instruction = "You are an expert product data analyst. Analyze product information accurately. Never fabricate specifications or evidence. If information is not available, mark it as missing. ALWAYS OUTPUT RAW JSON. DO NOT use <think> tags. Do not explain your reasoning. Output only the final response directly."

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "num_ctx": int(os.environ.get("OLLAMA_NUM_CTX", "2048")),
                "num_predict": -1,
            }
        }

        try:
            logger.info(f"\n[DIAGNOSTIC] Ollama POST /api/chat (analyze_product) | Provider: OLLAMA | Model: {self.model_name} | URL: {self.base_url}")
            response = await client.post(f"{self.base_url}/api/chat", json=payload, timeout=3600.0)
            response.raise_for_status()
            data = response.json()
            message = data.get("message", {})
            content = message.get("content", "")
            if not content.strip():
                content = message.get("thinking", "")
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(f"OllamaProvider analyze_product failed: {e}")
            raise RuntimeError(f"OllamaProvider analysis failed: {e}")

    @retry(retry=retry_if_exception(is_transient_error), stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def extract_attributes(
        self,
        product_info: dict[str, Any],
        evidence_texts: list[str],
        required_attributes: list[str],
    ) -> list[dict[str, Any]]:
        client = self._get_client()

        evidence_block = "\n---\n".join(evidence_texts[:5])

        prompt = f"""Extract product attributes from the provided evidence.

Product: {json.dumps(product_info, indent=2, default=str)}

Evidence:
{evidence_block}

Required Attributes: {json.dumps(required_attributes)}

For each attribute, return an object in a JSON array with these keys:
- "attribute": the attribute name
- "value": extracted value or null if not found
- "unit": unit of measurement if applicable
- "status": "DIRECTLY_SUPPORTED" if directly stated, "INFERRED" if inferred, "MISSING" if not found
- "evidence_snippet": the exact text that supports this value
- "source": which evidence source this came from
- "confidence": 0.0-1.0

CRITICAL RULES:
- NEVER invent values not supported by evidence
- Mark as MISSING if not found
- Mark as INFERRED if deduced but not directly stated
- Include the exact evidence snippet that supports each value

Output strictly a JSON array (or an object with an 'attributes' array). No markdown, no conversational text."""

        system_instruction = "You are a precise data extraction AI. Extract the requested attributes strictly from the provided evidence. ALWAYS OUTPUT RAW JSON. DO NOT use <think> tags. Do not explain your reasoning. Output only the final response directly."

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "num_ctx": int(os.environ.get("OLLAMA_NUM_CTX", "2048")),
                "num_predict": -1,
            }
        }

        try:
            logger.info(f"\n[DIAGNOSTIC] Ollama POST /api/chat (extract_attributes) | Provider: OLLAMA | Model: {self.model_name} | URL: {self.base_url}")
            response = await client.post(f"{self.base_url}/api/chat", json=payload, timeout=3600.0)
            logger.info(f"[DIAGNOSTIC] Ollama POST (extract_attributes) returned status: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content", "")
            result = self._parse_json_response(content)

            if isinstance(result, list):
                return result
            if isinstance(result, dict) and "attributes" in result:
                return result["attributes"]
            return [result] if isinstance(result, dict) else []
        except Exception as e:
            logger.error(f"OllamaProvider extract_attributes failed: {e}")
            raise RuntimeError(f"OllamaProvider extraction failed: {e}")

    def get_provider_name(self) -> str:
        return f"Ollama ({self.model_name})"

    @staticmethod
    def _parse_json_response(text: str, expected_type=dict) -> Any:
        """Robustly extract and parse JSON from Ollama output."""
        import re
        import json

        original_text = text
        # 1. Remove think blocks
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = re.sub(r'(?i)Thinking\.\.\..*?done thinking\.', '', text, flags=re.DOTALL)

        # 2. Robust JSON extraction
        valid_jsons = []
        decoder = json.JSONDecoder()

        i = 0
        while i < len(text):
            if text[i] in '{[':
                try:
                    obj, idx = decoder.raw_decode(text[i:])
                    if isinstance(obj, expected_type):
                        valid_jsons.append(obj)
                    i += idx
                    continue
                except json.JSONDecodeError:
                    pass
            i += 1

        if valid_jsons:
            if expected_type == dict:
                if len(valid_jsons) == 1:
                    return valid_jsons[0]
                # Merge all dicts (resolves LLMs splitting output into multiple blocks)
                merged = {}
                for d in valid_jsons:
                    merged.update(d)
                return merged
            else:
                return valid_jsons[-1]

        raise ValueError(f"Failed to extract JSON from Ollama response: {original_text[:200]}")


# ---------------------------------------------------------------------------
# FreeLLMAPI Provider (GPT-OSS 120B)
# ---------------------------------------------------------------------------

class FreeLLMAPIProvider(AIProviderInterface):
    """FreeLLMAPI provider targeting GPT-OSS 120B."""

    def __init__(self, base_url: str = "http://localhost:3001/v1", api_key: str = "", model: str = "gpt-oss-120b", timeout: int = 1200):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("FREELLMAPI_KEY", "")
        self.model_name = model or os.environ.get("FREELLMAPI_MODEL", "gpt-oss-120b")
        default_timeout = int(os.environ.get("PROVIDER_TIMEOUT_SECONDS", timeout))
        self.timeout = int(os.environ.get("FREELLMAPI_TIMEOUT_SECONDS", os.environ.get("FREELLMAPI_TIMEOUT", default_timeout)))
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    timeout=self.timeout,
                    max_retries=0
                )
            except ImportError:
                raise ImportError(
                    "openai package required. Install with: pip install openai"
                )
        return self._client

    @retry(retry=retry_if_exception(is_transient_error), stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def generate_structured(
        self,
        prompt: str,
        system_instruction: str = "",
        response_schema: Optional[dict] = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        client = self._get_client()

        full_prompt = prompt
        if response_schema:
            full_prompt += f"\n\nOutput STRICT valid JSON matching this schema. NO markdown, NO text, JUST JSON:\n{json.dumps(response_schema, indent=2)}"
        else:
            full_prompt += "\n\nOutput STRICT valid JSON. NO markdown, NO text, JUST JSON."

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": full_prompt})

        try:
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"} if response_schema else None
            )
            content = response.choices[0].message.content
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(f"FreeLLMAPIProvider generate_structured failed: {e}")
            raise RuntimeError(f"FreeLLMAPIProvider generation failed: {e}")

    @retry(retry=retry_if_exception(is_transient_error), stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    async def analyze_multimodal(
        self,
        prompt: str,
        image_paths: list[str] = None,
        audio_paths: list[str] = None,
        video_paths: list[str] = None,
        system_instruction: str = "",
        response_schema: Optional[dict] = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """FreeLLMAPI fallback for multimodal requests."""
        raise RuntimeError("Vision analysis unavailable in FreeLLMAPI mode")

    @retry(retry=retry_if_exception(is_transient_error), stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def analyze_product(
        self,
        product_info: dict[str, Any],
        task: str,
        context: str = "",
    ) -> dict[str, Any]:
        client = self._get_client()

        prompt = f"Task: {task}\n\nProduct Information:\n{json.dumps(product_info, indent=2, default=str)}\n\n"
        if context:
            prompt += f"Additional Context: {context}\n\n"

        prompt += "Respond with strictly valid JSON matching the exact requested keys. No surrounding text, no markdown."
        system_instruction = "You are an expert product data analyst. Analyze product information accurately. Never fabricate specifications or evidence. If information is not available, mark it as missing. ALWAYS OUTPUT RAW JSON."

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return self._parse_json_response(content)
        except Exception as e:
            logger.error(f"FreeLLMAPIProvider analyze_product failed: {e}")
            raise RuntimeError(f"FreeLLMAPIProvider analysis failed: {e}")

    @retry(retry=retry_if_exception(is_transient_error), stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def extract_attributes(
        self,
        product_info: dict[str, Any],
        evidence_texts: list[str],
        required_attributes: list[str],
    ) -> list[dict[str, Any]]:
        client = self._get_client()

        evidence_block = "\n---\n".join(evidence_texts[:5])

        prompt = f"""Extract product attributes from the provided evidence.

Product: {json.dumps(product_info, indent=2, default=str)}

Evidence:
{evidence_block}

Required Attributes: {json.dumps(required_attributes)}

For each attribute, return an object in a JSON array with these keys:
- "attribute": the attribute name
- "value": extracted value or null if not found
- "unit": unit of measurement if applicable
- "status": "DIRECTLY_SUPPORTED" if directly stated, "INFERRED" if inferred, "MISSING" if not found
- "evidence_snippet": the exact text that supports this value
- "source": which evidence source this came from
- "confidence": 0.0-1.0

CRITICAL RULES:
- NEVER invent values not supported by evidence
- Mark as MISSING if not found
- Mark as INFERRED if deduced but not directly stated
- Include the exact evidence snippet that supports each value

Output strictly a JSON array (or an object with an 'attributes' array). No markdown, no conversational text."""

        system_instruction = "You are an expert product data extraction system. Extract accurate values directly from the provided evidence texts. Never fabricate data. ALWAYS OUTPUT RAW JSON. DO NOT use <think> tags. Do not explain your reasoning. Output only the final response directly."

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]

        try:
            # We don't force json_object here since it might return an array at the root
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1
            )
            content = response.choices[0].message.content
            result = self._parse_json_response(content)

            if isinstance(result, list):
                return result
            if isinstance(result, dict) and "attributes" in result:
                return result["attributes"]
            return [result] if isinstance(result, dict) else []
        except Exception as e:
            logger.error(f"FreeLLMAPIProvider extract_attributes failed: {e}")
            raise RuntimeError(f"FreeLLMAPIProvider extraction failed: {e}")

    def get_provider_name(self) -> str:
        return f"FreeLLMAPI ({self.model_name})"

    @staticmethod
    def _parse_json_response(text: str) -> Any:
        """Robustly extract and parse JSON."""
        import re
        import json

        # 1. Remove think blocks
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = re.sub(r'(?i)Thinking\.\.\..*?done thinking\.', '', text, flags=re.DOTALL)

        # 2. Extract JSON from markdown blocks if present
        json_pattern = r'```(?:json)?(.*?)```'
        matches = re.findall(json_pattern, text, flags=re.DOTALL)
        if matches:
            text = matches[-1] # take the last code block

        text = text.strip()

        # 3. Try parsing directly
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 4. Fallback repair: find first {/[ and last }/]
        start_obj = text.find("{")
        start_arr = text.find("[")

        if start_obj == -1 and start_arr == -1:
            raise ValueError(f"No JSON object or array found in FreeLLMAPI response: {text[:200]}")

        start = start_obj if (start_arr == -1 or (start_obj != -1 and start_obj < start_arr)) else start_arr
        end_char = "}" if start == start_obj else "]"
        end = text.rfind(end_char)

        if end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse repaired JSON string: {e}")

        raise ValueError(f"Failed to extract JSON from FreeLLMAPI response: {text[:200]}")




# ---------------------------------------------------------------------------
# xAI Provider (Grok)
# ---------------------------------------------------------------------------

import time
import asyncio
from httpx import AsyncClient, HTTPStatusError, RequestError

class XAIError(Exception):
    pass

class XAIAuthenticationError(XAIError):
    pass

class XAIRateLimitError(XAIError):
    pass

class XAITimeoutError(XAIError):
    pass

class XAIServerError(XAIError):
    pass

class XAISchemaValidationError(XAIError):
    pass

class XAIProvider(AIProviderInterface):
    """xAI (Grok) API provider via httpx."""

    _last_request_time = 0.0
    _tpm_window_start = 0.0
    _tokens_used_in_window = 0
    _lock = asyncio.Lock()

    def __init__(self, api_key: str, model: str, max_rps: int = 5, max_tpm: int = 100000, timeout: int = 120):
        self.api_key = api_key
        self.model_name = model
        self.base_url = "https://api.x.ai"
        self.max_rps = max_rps
        self.max_tpm = max_tpm
        self.timeout = timeout
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = AsyncClient(timeout=self.timeout)
        return self._client

    async def _enforce_budget(self, estimated_tokens: int = 1000):
        """Enforce local safety limits (RPS and TPM)."""
        async with self._lock:
            now = time.time()

            # RPS check
            min_interval = 1.0 / self.max_rps if self.max_rps > 0 else 0
            elapsed = now - self.__class__._last_request_time
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)

            # TPM check
            if now - self.__class__._tpm_window_start > 60:
                self.__class__._tpm_window_start = now
                self.__class__._tokens_used_in_window = 0

            if self.__class__._tokens_used_in_window + estimated_tokens > self.max_tpm:
                sleep_time = 60 - (now - self.__class__._tpm_window_start)
                if sleep_time > 0:
                    logger.warning(f"XAIProvider TPM safety ceiling hit. Sleeping {sleep_time:.1f}s")
                    await asyncio.sleep(sleep_time)
                    # Reset window after sleep
                    self.__class__._tpm_window_start = time.time()
                    self.__class__._tokens_used_in_window = 0

            self.__class__._last_request_time = time.time()
            self.__class__._tokens_used_in_window += estimated_tokens

    async def _call_api_with_retry(self, payload: dict) -> dict:
        """Call xAI API with bounded exponential backoff for 429 errors."""
        max_retries = 3
        base_delay = 2.0

        client = self._get_client()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        for attempt in range(max_retries + 1):
            await self._enforce_budget()
            try:
                response = await client.post(f"{self.base_url}/v1/chat/completions", json=payload, headers=headers)

                if response.status_code in (401, 403):
                    raise XAIAuthenticationError(f"xAI Auth Error: {response.status_code} - {response.text}")
                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else base_delay * (2 ** attempt)
                    if attempt < max_retries:
                        logger.warning(f"xAI Rate Limit (429). Retrying in {delay}s (attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise XAIRateLimitError(f"xAI Rate Limit exceeded after {max_retries} retries.")
                elif response.status_code >= 500:
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"xAI Server Error {response.status_code}. Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        raise XAIServerError(f"xAI Server Error: {response.status_code} - {response.text}")

                response.raise_for_status()
                return response.json()

            except RequestError as e:
                # E.g., network timeouts
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"xAI Request/Timeout Error: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise XAITimeoutError(f"xAI Network/Timeout Error: {e}")

        raise XAIError("Unexpected end of retry loop")

    async def generate_structured(
        self,
        prompt: str,
        system_instruction: str = "",
        response_schema: Optional[dict] = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }

        if response_schema:
            schema_name = response_schema.get("title", "structured_response").replace(" ", "_")
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": response_schema,
                    "strict": True
                }
            }

        data = await self._call_api_with_retry(payload)

        try:
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            return result
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise XAISchemaValidationError(f"Failed to parse xAI response as JSON: {e}\nRaw data: {data}")

    async def analyze_multimodal(
        self,
        prompt: str,
        image_paths: list[str] = None,
        audio_paths: list[str] = None,
        video_paths: list[str] = None,
        system_instruction: str = "",
        response_schema: Optional[dict] = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """xAI grok-4.5 local fallback for multimodal if xAI vision is not fully configured."""
        if response_schema:
            logger.warning(f"xAI provider received multimodal request. Attempting graceful fallback.")
            fallback = {}
            for key in response_schema.get("properties", {}).keys():
                if response_schema["properties"][key].get("type") == "array":
                    fallback[key] = []
                elif response_schema["properties"][key].get("type") == "string":
                    fallback[key] = "Vision analysis unavailable for xAI"
                else:
                    fallback[key] = None
            return fallback
        return {"error": "Vision analysis unavailable for xAI"}

    async def analyze_product(
        self,
        product_info: dict[str, Any],
        task: str,
        context: str = "",
    ) -> dict[str, Any]:

        prompt = f"Task: {task}\n\nProduct Information:\n{json.dumps(product_info, indent=2, default=str)}\n\n"
        if context:
            prompt += f"Additional Context: {context}\n\n"

        system_instruction = "You are an expert product data analyst. Analyze product information accurately. Never fabricate specifications or evidence. If information is not available, mark it as missing."

        return await self.generate_structured(
            prompt=prompt,
            system_instruction=system_instruction,
            response_schema={"type": "object", "additionalProperties": True}, # Fallback schema if not explicitly provided
            temperature=0.2
        )

    async def extract_attributes(
        self,
        product_info: dict[str, Any],
        evidence_texts: list[str],
        required_attributes: list[str],
    ) -> list[dict[str, Any]]:

        evidence_block = "\n---\n".join(evidence_texts[:5])

        prompt = f"""Extract product attributes from the provided evidence.

Product: {json.dumps(product_info, indent=2, default=str)}

Evidence:
{evidence_block}

Required Attributes: {json.dumps(required_attributes)}

CRITICAL RULES:
- NEVER invent values not supported by evidence
- Mark as MISSING if not found
- Mark as INFERRED if deduced but not directly stated
- Include the exact evidence snippet that supports each value
"""
        system_instruction = "You are a precise product data extraction engine. Extract only what is directly supported by evidence. Never fabricate data."

        schema = {
            "type": "object",
            "properties": {
                "attributes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "attribute": {"type": "string"},
                            "value": {"type": ["string", "number", "null"]},
                            "unit": {"type": ["string", "null"]},
                            "status": {"type": "string", "enum": ["DIRECTLY_SUPPORTED", "INFERRED", "MISSING"]},
                            "evidence_snippet": {"type": ["string", "null"]},
                            "source": {"type": ["string", "null"]},
                            "confidence": {"type": "number"}
                        },
                        "required": ["attribute", "value", "unit", "status", "evidence_snippet", "source", "confidence"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["attributes"],
            "additionalProperties": False
        }

        result = await self.generate_structured(
            prompt=prompt,
            system_instruction=system_instruction,
            response_schema=schema,
            temperature=0.1
        )

        return result.get("attributes", [])

    def get_provider_name(self) -> str:
        return f"xAI ({self.model_name})"

