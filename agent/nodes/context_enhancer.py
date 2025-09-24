"""
Context enhancer node for the search agent graph.

This node enhances queries with conversation context from previous interactions.
"""

import logging
from typing import Dict, Any, List, Optional

from memory.conversation_memory import conversation_memory

logger = logging.getLogger(__name__)

def enhance_with_context(query: str, session_id: str) -> Dict[str, Any]:
    """
    Enhance a query with conversation context.
    
    Args:
        query: The original user query
        session_id: The conversation session ID
        
    Returns:
        Dictionary with enhanced query and context information
    """
    # Add the user message to conversation memory
    conversation_memory.add_user_message(session_id, query)
    
    # Get enhanced query with conversation context
    enhanced_query, recent_history = conversation_memory.get_context_for_query(session_id, query)
    
    # Create a context object to pass through the graph
    context = {
        "original_query": query,
        "enhanced_query": enhanced_query,
        "session_id": session_id,
        "has_context": len(recent_history) > 0,
        "recent_history": recent_history
    }
    
    logger.info(f"Enhanced query with conversation context for session {session_id}")
    return context
