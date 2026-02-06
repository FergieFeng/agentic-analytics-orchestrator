"""
LLM Client: Unified interface for calling language models.

Uses LangChain for LLM abstraction and supports:
- OpenAI (GPT-4, GPT-4o, GPT-3.5)
- Anthropic (Claude) - extensible

Features:
- LangChain ChatOpenAI integration
- PromptTemplate support
- RAG context injection
- Token tracking
"""

import json
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from functools import lru_cache

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

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


class LangChainLLM:
    """
    LangChain-based LLM client.
    
    Usage:
        llm = LangChainLLM()
        
        # Simple completion
        response = llm.complete(
            system_prompt="You are a helpful assistant.",
            user_prompt="What is net flow?"
        )
        
        # With RAG context
        response = llm.complete_with_context(
            system_prompt="...",
            user_prompt="...",
            context="Retrieved knowledge..."
        )
        
        # Using prompt templates
        template = llm.create_prompt_template(
            "Answer based on: {context}\n\nQuestion: {question}"
        )
        response = llm.invoke_template(template, context="...", question="...")
    """
    
    def __init__(self):
        self.model_name = settings.model_name
        self.temperature = settings.temperature
        self.max_tokens = settings.max_tokens
        
        # Initialize LangChain ChatOpenAI
        self._chat_model = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            openai_api_key=settings.openai_api_key
        )
        
        # Track token usage
        self._last_usage: Dict[str, int] = {}
    
    @property
    def chat_model(self) -> ChatOpenAI:
        """Get the underlying ChatOpenAI model."""
        return self._chat_model
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> LLMResponse:
        """
        Send a chat completion request using LangChain.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            json_mode: Request JSON response format
            
        Returns:
            LLMResponse with content and metadata
        """
        # Convert to LangChain message format
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))
        
        # Configure model for this call
        model = self._chat_model
        if temperature is not None or max_tokens is not None:
            model = ChatOpenAI(
                model=self.model_name,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                openai_api_key=settings.openai_api_key
            )
        
        # Add JSON mode if requested
        if json_mode:
            model = model.bind(response_format={"type": "json_object"})
        
        # Invoke model
        response = model.invoke(lc_messages)
        
        # Extract token usage from response metadata
        usage = {}
        if hasattr(response, 'response_metadata'):
            token_usage = response.response_metadata.get('token_usage', {})
            usage = {
                "prompt_tokens": token_usage.get('prompt_tokens', 0),
                "completion_tokens": token_usage.get('completion_tokens', 0),
                "total_tokens": token_usage.get('total_tokens', 0),
            }
        self._last_usage = usage
        
        return LLMResponse(
            content=response.content,
            model=self.model_name,
            usage=usage
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
    
    def complete_with_context(
        self,
        system_prompt: str,
        user_prompt: str,
        context: str,
        temperature: Optional[float] = None,
        json_mode: bool = False
    ) -> LLMResponse:
        """
        Completion with RAG context injected.
        
        Args:
            system_prompt: System instructions
            user_prompt: User message
            context: Retrieved context from RAG
            temperature: Override default temperature
            json_mode: Request JSON response format
            
        Returns:
            LLMResponse
        """
        # Inject context into user prompt
        augmented_prompt = f"""## Retrieved Context
{context}

## User Question
{user_prompt}"""
        
        return self.complete(
            system_prompt=system_prompt,
            user_prompt=augmented_prompt,
            temperature=temperature,
            json_mode=json_mode
        )
    
    def create_prompt_template(
        self,
        template: str,
        input_variables: Optional[List[str]] = None
    ) -> PromptTemplate:
        """
        Create a LangChain PromptTemplate.
        
        Args:
            template: Template string with {variables}
            input_variables: List of variable names (auto-detected if not provided)
            
        Returns:
            PromptTemplate instance
        """
        if input_variables is None:
            # Auto-detect variables from template
            import re
            input_variables = re.findall(r'\{(\w+)\}', template)
        
        return PromptTemplate(
            template=template,
            input_variables=input_variables
        )
    
    def create_chat_prompt_template(
        self,
        system_template: str,
        user_template: str
    ) -> ChatPromptTemplate:
        """
        Create a LangChain ChatPromptTemplate.
        
        Args:
            system_template: System message template
            user_template: User message template
            
        Returns:
            ChatPromptTemplate instance
        """
        return ChatPromptTemplate.from_messages([
            ("system", system_template),
            ("human", user_template)
        ])
    
    def invoke_template(
        self,
        template: Union[PromptTemplate, ChatPromptTemplate],
        json_mode: bool = False,
        **kwargs
    ) -> LLMResponse:
        """
        Invoke a prompt template with variables.
        
        Args:
            template: PromptTemplate or ChatPromptTemplate
            json_mode: Request JSON response format
            **kwargs: Template variables
            
        Returns:
            LLMResponse
        """
        # Format the template
        if isinstance(template, ChatPromptTemplate):
            messages = template.format_messages(**kwargs)
            model = self._chat_model
            if json_mode:
                model = model.bind(response_format={"type": "json_object"})
            response = model.invoke(messages)
        else:
            prompt_text = template.format(**kwargs)
            return self.complete(
                system_prompt="",
                user_prompt=prompt_text,
                json_mode=json_mode
            )
        
        # Extract usage
        usage = {}
        if hasattr(response, 'response_metadata'):
            token_usage = response.response_metadata.get('token_usage', {})
            usage = {
                "prompt_tokens": token_usage.get('prompt_tokens', 0),
                "completion_tokens": token_usage.get('completion_tokens', 0),
                "total_tokens": token_usage.get('total_tokens', 0),
            }
        
        return LLMResponse(
            content=response.content,
            model=self.model_name,
            usage=usage
        )
    
    def get_last_usage(self) -> Dict[str, int]:
        """Get token usage from last call."""
        return self._last_usage


# Backward compatibility: LLMClient alias
class LLMClient(LangChainLLM):
    """Alias for backward compatibility."""
    pass


# Global client instance (lazy loaded)
_client: Optional[LangChainLLM] = None


@lru_cache(maxsize=1)
def get_llm_client() -> LangChainLLM:
    """Get or create the LLM client."""
    return LangChainLLM()


# Convenience function for RAG-augmented completion
def complete_with_rag(
    question: str,
    system_prompt: str,
    k_knowledge: int = 5,
    k_schema: int = 3,
    json_mode: bool = False
) -> LLMResponse:
    """
    Complete with automatic RAG retrieval.
    
    Args:
        question: User question
        system_prompt: System instructions
        k_knowledge: Number of knowledge chunks to retrieve
        k_schema: Number of schema chunks to retrieve
        json_mode: Request JSON response format
        
    Returns:
        LLMResponse with RAG-augmented context
    """
    from src.rag import retrieve_context
    
    # Retrieve context
    context = retrieve_context(question, k_knowledge, k_schema)
    
    # Complete with context
    client = get_llm_client()
    return client.complete_with_context(
        system_prompt=system_prompt,
        user_prompt=question,
        context=context,
        json_mode=json_mode
    )


if __name__ == "__main__":
    # Test LangChain LLM
    client = get_llm_client()
    
    print("Testing LangChain LLM client...")
    
    # Simple completion
    response = client.complete(
        system_prompt="You are a helpful assistant.",
        user_prompt="Say 'Hello, LangChain!' in exactly 3 words."
    )
    
    print(f"Response: {response.content}")
    print(f"Model: {response.model}")
    print(f"Tokens: {response.usage}")
    
    # Test with template
    print("\nTesting prompt template...")
    template = client.create_chat_prompt_template(
        system_template="You are a {role}.",
        user_template="Answer this: {question}"
    )
    
    response = client.invoke_template(
        template,
        role="banking analytics expert",
        question="What is net flow?"
    )
    
    print(f"Response: {response.content[:100]}...")
