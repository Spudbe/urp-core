"""Provider-agnostic LLM adapter interface for URP agents.

This module defines an abstract base class for LLM adapters and a concrete
implementation using the Groq API. Any LLM provider can be integrated by
subclassing ``LLMAdapter`` and implementing the ``complete`` method.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters.

    Subclasses must implement the ``complete`` method, which accepts a system
    prompt and a user prompt and returns the model's text response.
    """

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a system prompt and user prompt to the LLM and return the response text.

        Args:
            system_prompt: Instructions that set the model's behaviour and role.
            user_prompt: The user-facing query or task for the model to respond to.

        Returns:
            The model's text response as a string.
        """


class GroqAdapter(LLMAdapter):
    """LLM adapter that calls the Groq API using the ``groq`` Python package.

    Reads the API key from the ``GROQ_API_KEY`` environment variable.
    Uses the ``llama-3.3-70b-versatile`` model by default.

    Args:
        model: The Groq model identifier to use. Defaults to ``"llama-3.3-70b-versatile"``.
    """

    def __init__(self, model: str = "llama-3.3-70b-versatile") -> None:
        self.model = model
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY environment variable is not set. "
                "Get a key at https://console.groq.com and export it."
            )
        from groq import Groq
        self._client = Groq(api_key=api_key)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a completion request to the Groq API.

        Args:
            system_prompt: Instructions that set the model's behaviour and role.
            user_prompt: The user-facing query or task for the model to respond to.

        Returns:
            The model's text response as a string.
        """
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=512,
        )
        return response.choices[0].message.content.strip()
