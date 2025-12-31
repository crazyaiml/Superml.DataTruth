"""
LLM Client - OpenAI and Azure OpenAI integration

Provides a unified interface for interacting with LLMs.
"""

import json
from typing import Any, Dict, List, Optional

from openai import AzureOpenAI, OpenAI
from pydantic import BaseModel

from src.config import settings


class LLMClient:
    """Client for interacting with OpenAI or Azure OpenAI."""

    def __init__(self) -> None:
        """Initialize the LLM client based on configuration."""
        # Debug: write to file since logging isn't working
        with open('/tmp/llm_init_debug.txt', 'w') as f:
            f.write(f"LLMClient init called\n")
            f.write(f"settings.openai_api_key length: {len(settings.openai_api_key) if settings.openai_api_key else 0}\n")
            f.write(f"settings.openai_api_key: {settings.openai_api_key[:50] if settings.openai_api_key else 'EMPTY'}\n")
        
        if settings.use_azure_openai:
            self.client = AzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint,
            )
            self.model = settings.azure_openai_deployment
            self.provider = "azure"
        else:
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.model = settings.openai_model
            self.provider = "openai"

        self.temperature = settings.openai_temperature
        self.max_tokens = settings.openai_max_tokens

    def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Get completion from LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max tokens
            response_format: Optional response format (e.g., {"type": "json_object"})

        Returns:
            Response content as string
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def complete_json(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get JSON completion from LLM.

        Args:
            messages: List of message dicts
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            Parsed JSON response

        Raises:
            ValueError: If response is not valid JSON
        """
        response = self.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        # Strip markdown code blocks if present
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]  # Remove ```json
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]  # Remove ```
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]  # Remove trailing ```
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from LLM response: {cleaned_response}") from e

    def complete_structured(
        self,
        messages: List[Dict[str, str]],
        model_class: type[BaseModel],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> BaseModel:
        """
        Get structured Pydantic model from LLM.

        Args:
            messages: List of message dicts
            model_class: Pydantic model class to parse into
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            Parsed Pydantic model instance

        Raises:
            ValueError: If response cannot be parsed into model
        """
        json_response = self.complete_json(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            return model_class(**json_response)
        except Exception as e:
            raise ValueError(
                f"Failed to validate response against {model_class.__name__} model: {json_response}"
            ) from e


def create_messages(
    prompt: str,
    system_prompt: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Create messages list from prompt and optional system prompt.

    Args:
        prompt: User prompt
        system_prompt: Optional system prompt

    Returns:
        List of message dicts
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return messages


# Global LLM client instance
_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Get the global LLM client instance.

    Returns:
        LLMClient instance
    """
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
