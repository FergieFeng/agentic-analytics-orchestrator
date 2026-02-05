"""
LLM Client: Unified interface for calling language models.

Supports OpenAI and Anthropic (extensible to others).
"""

import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from openai import OpenAI
from src.config.settings import settings


@dataclass
class LLMResponse:
    """Response from LLM call."""
    content: str
    model: str
    usage: Dict[str, int]
    
    def to_json(self) -> Optional[Dict]:
        """Try to parse content as JSON."""
        try:
            # Try to extract JSON from markdown code block
            content = self.content
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()
            
            return json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return None


class LLMClient:
    """Client for making LLM API calls."""
    
    def __init__(self):
        self.provider = settings.llm_provider
        self.model = settings.model_name
        self.temperature = settings.temperature
        self.max_tokens = settings.max_tokens
        
        if self.provider == "openai":
            self.client = OpenAI(api_key=settings.openai_api_key)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> LLMResponse:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            json_mode: Request JSON response format
            
        Returns:
            LLMResponse with content and metadata
        """
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = self.client.chat.completions.create(**kwargs)
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        )
    
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        json_mode: bool = False
    ) -> LLMResponse:
        """
        Simple completion with system and user prompts.
        
        Args:
            system_prompt: System instructions
            user_prompt: User message
            temperature: Override default temperature
            json_mode: Request JSON response format
            
        Returns:
            LLMResponse
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self.chat(messages, temperature=temperature, json_mode=json_mode)


# Global client instance (lazy loaded)
_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the LLM client."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


if __name__ == "__main__":
    client = get_llm_client()
    
    response = client.complete(
        system_prompt="You are a helpful assistant.",
        user_prompt="Say 'Hello, analytics!' in exactly 3 words."
    )
    
    print(f"Response: {response.content}")
    print(f"Model: {response.model}")
    print(f"Tokens: {response.usage}")
