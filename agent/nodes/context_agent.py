"""
Context Agent - Intelligently analyzes conversation context using LLM
"""

import logging
import json
from typing import Dict, List, Any, Optional
from langchain_core.language_models import BaseLanguageModel
from configs.load import get_default_llm

logger = logging.getLogger(__name__)

class ContextAgent:
    """Intelligent context analysis agent that understands conversation flow"""
    
    def __init__(self, llm: Optional[BaseLanguageModel] = None):
        self.llm = llm or get_default_llm()
    
    def analyze_conversation_context(self, session_id: str, current_query: str, 
                                   conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze conversation context using LLM-based understanding.
        
        Args:
            session_id: Unique session identifier
            current_query: The current user query
            conversation_history: List of previous conversation turns
            
        Returns:
            Dictionary with intelligent context analysis
        """
        if not conversation_history:
            return {
                "is_follow_up": False,
                "conversation_topic": None,
                "context_summary": "This is the start of a new conversation.",
                "relevant_entities": [],
                "query_intent": "initial_query",
                "context_relevance": "none",
                "suggested_workflow_type": "simple_search"
            }
        
        # Build conversation summary for LLM analysis
        conversation_text = self._build_conversation_text(conversation_history)
        
        # Use LLM to analyze the conversation context
        context_analysis = self._llm_analyze_context(current_query, conversation_text)
        
        return context_analysis
    
    def _build_conversation_text(self, history: List[Dict[str, Any]]) -> str:
        """Build a readable conversation summary from history."""
        conversation_parts = []
        
        for i, turn in enumerate(history[-6:]):  # Last 6 turns for context
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            timestamp = turn.get("timestamp", "")
            
            if role == "user":
                conversation_parts.append(f"User: {content}")
            elif role == "assistant":
                # Truncate long assistant responses
                if len(content) > 200:
                    content = content[:200] + "..."
                conversation_parts.append(f"Assistant: {content}")
        
        return "\n".join(conversation_parts)
    
    def _llm_analyze_context(self, current_query: str, conversation_text: str) -> Dict[str, Any]:
        """Use LLM to analyze conversation context intelligently."""
        try:
            prompt = f"""
You are an expert conversation analyst. Analyze the following conversation and the current query to understand the context and determine if this is a follow-up question.

CONVERSATION HISTORY:
{conversation_text}

CURRENT QUERY:
{current_query}

Analyze this conversation and answer the following questions:

1. Is the current query a follow-up to the previous conversation? (Yes/No)
2. What is the main topic or theme of this conversation?
3. What are the key entities, concepts, or topics mentioned?
4. What is the intent of the current query in relation to the conversation?
5. How relevant is the current query to the conversation context? (high/medium/low/none)
6. Based on the context, what type of workflow would be most appropriate? (simple_search/complex_filtering/computation_required/monitoring_workflow)

Return your analysis as a JSON object with the following structure:
{{
    "is_follow_up": true/false,
    "conversation_topic": "main topic of conversation",
    "context_summary": "brief summary of conversation context",
    "relevant_entities": ["entity1", "entity2", "entity3"],
    "query_intent": "intent of current query",
    "context_relevance": "high/medium/low/none",
    "suggested_workflow_type": "simple_search/complex_filtering/computation_required/monitoring_workflow",
    "reasoning": "explanation of the analysis"
}}

Examples:
- If someone asks "What does that mean?" after discussing 10K reports, it's a follow-up asking for clarification
- If someone asks "Tell me more about Samsung" after discussing financial statements, it's a follow-up for more details
- If someone asks "Hello" after any conversation, it's not a follow-up but a greeting
"""

            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            # Remove any control characters that might cause JSON parsing issues
            import re
            content = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content.strip())
            
            # Try to find JSON object boundaries
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_content = content[start_idx:end_idx + 1]
                result = json.loads(json_content)
                
                logger.info(f"Context analysis: {result}")
                return result
            else:
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            logger.error(f"Context analysis failed: {e}")
            # Fallback to basic analysis
            return self._fallback_context_analysis(current_query, conversation_text)
    
    def _fallback_context_analysis(self, current_query: str, conversation_text: str) -> Dict[str, Any]:
        """Fallback context analysis when LLM fails."""
        query_lower = current_query.lower()
        
        # Basic follow-up detection
        follow_up_indicators = [
            "what does that mean", "what do you mean", "explain", "clarify",
            "tell me more", "more about", "also", "additionally", "what about",
            "그게 무슨 말이야", "무슨 말이야", "뭐라는 거야", "무슨 뜻이야",
            "설명해줘", "자세히 말해줘", "더 자세히", "그게 뭔데"
        ]
        
        is_follow_up = any(indicator in query_lower for indicator in follow_up_indicators)
        
        return {
            "is_follow_up": is_follow_up,
            "conversation_topic": "general discussion",
            "context_summary": "Previous conversation context available.",
            "relevant_entities": [],
            "query_intent": "information_request",
            "context_relevance": "medium" if is_follow_up else "low",
            "suggested_workflow_type": "simple_search",
            "reasoning": "Fallback analysis due to LLM failure"
        }


def analyze_conversation_context(session_id: str, current_query: str, 
                               conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze conversation context using the Context Agent."""
    agent = ContextAgent()
    return agent.analyze_conversation_context(session_id, current_query, conversation_history)
