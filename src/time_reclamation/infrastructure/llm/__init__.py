"""
LLM Infrastructure Module

This module provides a high-level interface for interacting with various
Large Language Model providers, allowing easy switching between different
LLM services and local models.
"""

from .interface import LLMProvider, LLMResult, LLMStatus
from .manager import LLMManager, get_llm_manager, generate_llm_response

__all__ = [
    'LLMProvider',
    'LLMResult', 
    'LLMStatus',
    'LLMManager',
    'get_llm_manager',
    'generate_llm_response'
]