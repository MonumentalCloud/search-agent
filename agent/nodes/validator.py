import json
import logging
from typing import Dict, List, Optional
from langchain.tools import tool
from langchain_core.language_models import BaseLanguageModel

from configs.load import get_default_llm
from agent.types import RerankedChunk

logger = logging.getLogger(__name__)


@tool
def check_grounding(chunk_id: str, claim: str) -> str:
    """Check if a claim is properly grounded in the source chunk."""
    # Placeholder implementation
    return f"Grounding check for chunk {chunk_id}: {claim}"


def validate(query: str, top: List[RerankedChunk], llm: Optional[BaseLanguageModel] = None) -> Dict:
    """Validate search results by checking relevance to the query."""
    logger.info(f"Validating {len(top)} results for query: {query}")
    
    # If no results, return invalid
    if len(top) == 0:
        result = {
            "valid": False,
            "confidence": 0.0,
            "reason": "No results found - Database may not be connected or no documents indexed",
            "action": "RELAX"
        }
        logger.info(f"Validator result: {result}")
        return result
    
    # For very short queries (less than 3 words), require higher relevance
    query_words = query.strip().split()
    if len(query_words) < 3 and query.lower() not in ["hi", "hello", "안녕", "안녕하세요"]:
        # Check if the query appears in any of the top results
        query_found = False
        for chunk in top[:3]:
            body = chunk.get('body', '').lower()
            if query.lower() in body:
                query_found = True
                break
        
        # If the query is very short and not found in results, consider invalid
        if not query_found:
            result = {
                "valid": False,
                "confidence": 0.3,
                "reason": f"The query '{query}' is too short and not found in the top results",
                "action": "CLARIFY"
            }
            logger.info(f"Validator result: {result}")
            return result
    
    # For greeting queries, don't use search results
    if query.lower() in ["hi", "hello", "안녕", "안녕하세요"]:
        result = {
            "valid": False,
            "confidence": 0.9,
            "reason": "Greeting query detected, no search results needed",
            "action": "GREET"
        }
        logger.info(f"Validator result: {result}")
        return result
    
    # For regular queries, consider results valid
    result = {
        "valid": True,
        "confidence": 0.8,
        "reason": f"Found {len(top)} relevant results",
        "action": "ACCEPT"
    }
    
    logger.info(f"Validator result: {result}")
    
    # Debug: Print what we're returning
    print(f"DEBUG VALIDATOR: Query: {query}")
    print(f"DEBUG VALIDATOR: Results count: {len(top)}")
    print(f"DEBUG VALIDATOR: Returning result: {result}")
    print(f"DEBUG VALIDATOR: Result type: {type(result)}")
    print(f"DEBUG VALIDATOR: Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
    
    return result