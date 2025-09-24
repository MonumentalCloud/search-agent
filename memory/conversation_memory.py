"""
Conversation memory store for multi-turn conversations.

This module provides a simple in-memory database for storing conversation history
and generating context-aware summaries for the agent.
"""

import logging
import time
import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import json

logger = logging.getLogger(__name__)

class ConversationMemory:
    """Store and manage conversation history for multi-turn interactions."""
    
    def __init__(self, max_history_length: int = 50, max_summary_tokens: int = 500, max_long_term_memory: int = 200, db_path: str = "conversation_memory.db"):
        """
        Initialize the conversation memory store.
        
        Args:
            max_history_length: Maximum number of turns to keep in recent history
            max_summary_tokens: Maximum tokens to include in the summary
            max_long_term_memory: Maximum number of messages to keep for long-term reference
            db_path: Path to SQLite database for persistence
        """
        self._conversations: Dict[str, Dict[str, Any]] = {}
        self._max_history_length = max_history_length
        self._max_summary_tokens = max_summary_tokens
        self._max_long_term_memory = max_long_term_memory
        self.db_path = db_path
        
        # Track entities and intents across conversations for better context
        self._entity_tracker: Dict[str, List[str]] = {}  # session_id -> list of entities
        self._intent_tracker: Dict[str, List[str]] = {}  # session_id -> list of intents
        self._document_references: Dict[str, List[Dict]] = {}  # session_id -> list of cited documents
        
        self._init_database()
        self._load_conversations_from_db()
    
    def add_user_message(self, session_id: str, message: str) -> None:
        """
        Add a user message to the conversation history.
        
        Args:
            session_id: Unique identifier for the conversation
            message: The user's message
        """
        if session_id not in self._conversations:
            self._conversations[session_id] = {
                "history": [],
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        
        self._conversations[session_id]["history"].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        self._conversations[session_id]["last_updated"] = datetime.now().isoformat()
        self._trim_history(session_id)
        
        # Save to database
        self._save_conversation_to_db(session_id)
    
    def add_assistant_message(self, session_id: str, message: str, citations: List[Dict[str, Any]] = None) -> None:
        """
        Add an assistant message to the conversation history.
        
        Args:
            session_id: Unique identifier for the conversation
            message: The assistant's message
            citations: Optional list of citations used in the response
        """
        if session_id not in self._conversations:
            logger.warning(f"Adding assistant message to non-existent session {session_id}")
            self._conversations[session_id] = {
                "history": [],
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        
        self._conversations[session_id]["history"].append({
            "role": "assistant",
            "content": message,
            "citations": citations or [],
            "timestamp": datetime.now().isoformat()
        })
        
        self._conversations[session_id]["last_updated"] = datetime.now().isoformat()
        self._trim_history(session_id)
        
        # Save to database
        self._save_conversation_to_db(session_id)
    
    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the full conversation history for a session.
        
        Args:
            session_id: Unique identifier for the conversation
            
        Returns:
            List of message objects in the conversation
        """
        if session_id not in self._conversations:
            return []
        
        return self._conversations[session_id]["history"]
    
    def get_context_for_query(self, session_id: str, current_query: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Get conversation context to enhance the current query.
        
        Args:
            session_id: Unique identifier for the conversation
            current_query: The current user query
            
        Returns:
            Tuple of (enhanced query with context, recent history)
        """
        if session_id not in self._conversations:
            return current_query, []
        
        history = self._conversations[session_id]["history"]
        if not history:
            return current_query, []
        
        # Get the last few turns for immediate context
        recent_history = history[-min(4, len(history)):]
        
        # Extract document references and citations from previous assistant responses
        doc_references = []
        for msg in recent_history:
            if msg.get("role") == "assistant":
                citations = msg.get("citations", [])
                for citation in citations:
                    doc_id = citation.get("doc_id")
                    if doc_id and doc_id not in doc_references:
                        doc_references.append(doc_id)
        
        # Create a summary of the conversation
        summary = self._generate_conversation_summary(history)
        
        # Enhance the query with the conversation context
        enhanced_query = f"{current_query}\n\nConversation context: {summary}"
        
        # If there are document references, add them to the enhanced query
        if doc_references:
            doc_context = f"\n\nPreviously discussed documents: {', '.join(doc_references)}"
            enhanced_query += doc_context
        
        return enhanced_query, recent_history
    
    def get_advanced_context_for_meta_agent(self, session_id: str, current_query: str) -> Dict[str, Any]:
        """
        Get advanced conversation context specifically for Meta Agent analysis.
        Uses intelligent Context Agent instead of rule-based extraction.
        
        Args:
            session_id: Unique identifier for the conversation
            current_query: The current user query
            
        Returns:
            Dictionary with comprehensive context information
        """
        if session_id not in self._conversations:
            return {
                "query": current_query,
                "conversation_history": [],
                "context_analysis": {
                    "is_follow_up": False,
                    "conversation_topic": None,
                    "context_summary": "This is the start of a new conversation.",
                    "relevant_entities": [],
                    "query_intent": "initial_query",
                    "context_relevance": "none",
                    "suggested_workflow_type": "simple_search"
                }
            }
        
        history = self._conversations[session_id]["history"]
        
        # Use Context Agent for intelligent analysis
        from agent.nodes.context_agent import analyze_conversation_context
        context_analysis = analyze_conversation_context(session_id, current_query, history)
        
        return {
            "query": current_query,
            "conversation_history": history[-min(self._max_long_term_memory, len(history)):],
            "context_analysis": context_analysis
        }
    
    def _extract_entities_from_history(self, history: List[Dict[str, Any]]) -> List[str]:
        """Extract entities from conversation history."""
        entities = set()
        
        for msg in history:
            content = msg.get("content", "")
            # Simple entity extraction - look for capitalized words and specific patterns
            import re
            
            # Extract capitalized words (potential entities)
            capitalized_words = re.findall(r'\b[A-Z][a-z]+\b', content)
            entities.update(capitalized_words)
            
            # Extract meeting dates
            dates = re.findall(r'\d{4}-\d{2}-\d{2}', content)
            entities.update(dates)
            
            # Extract document IDs
            doc_ids = re.findall(r'회의록_\d+_[가-힣]+', content)
            entities.update(doc_ids)
        
        return list(entities)
    
    def _extract_intents_from_history(self, history: List[Dict[str, Any]]) -> List[str]:
        """Extract intents from conversation history."""
        intents = []
        
        for msg in history:
            content = msg.get("content", "").lower()
            
            # Simple intent detection
            if any(word in content for word in ['meeting', '회의', '회의록']):
                intents.append("meeting_search")
            if any(word in content for word in ['when', '언제', 'date', '날짜']):
                intents.append("temporal_query")
            if any(word in content for word in ['who', '누구', 'attendee', '참석자']):
                intents.append("people_query")
            if any(word in content for word in ['what', '뭐', 'decision', '결정']):
                intents.append("content_query")
            if any(word in content for word in ['risk', '리스크', 'investment', '투자']):
                intents.append("financial_query")
        
        return list(set(intents))
    
    def _extract_document_references(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract document references from conversation history."""
        references = []
        
        for msg in history:
            if msg.get("role") == "assistant":
                citations = msg.get("citations", [])
                for citation in citations:
                    if citation not in references:
                        references.append(citation)
        
        return references
    
    def _analyze_query_context(self, current_query: str, recent_history: List[Dict[str, Any]], 
                              entities: List[str], intents: List[str]) -> Dict[str, Any]:
        """Analyze the current query in context of conversation history."""
        analysis = {
            "is_follow_up": False,
            "has_references": False,
            "conversation_topic": None,
            "query_dependencies": [],
            "entity_co_references": [],
            "intent_continuity": False
        }
        
        # Check for follow-up indicators
        follow_up_indicators = [
            "tell me more", "more about", "also", "additionally", "what about",
            "what does that mean", "what do you mean", "explain that", "clarify",
            "그것에 대해 더", "또한", "추가로", "그리고", "그건", "그것은",
            "그게 무슨 말이야", "무슨 말이야", "뭐라는 거야", "무슨 뜻이야",
            "설명해줘", "자세히 말해줘", "더 자세히", "그게 뭔데"
        ]
        
        query_lower = current_query.lower()
        analysis["is_follow_up"] = any(indicator in query_lower for indicator in follow_up_indicators)
        
        # Check for entity references
        for entity in entities:
            entity_lower = entity.lower()
            # Check if entity appears in query (direct match or word match)
            if (entity_lower in query_lower or 
                any(word in query_lower for word in entity_lower.split()) or
                any(word in entity_lower for word in query_lower.split())):
                analysis["entity_co_references"].append(entity)
                analysis["has_references"] = True
        
        # Also check for common reference words
        reference_words = ["that", "this", "it", "the", "those", "these", "그것", "그", "이것", "저것"]
        if any(word in query_lower for word in reference_words):
            analysis["has_references"] = True
        
        # Check for intent continuity
        current_intent = self._detect_current_intent(current_query)
        analysis["intent_continuity"] = current_intent in intents if intents else False
        
        # Determine conversation topic
        if intents:
            analysis["conversation_topic"] = intents[-1]  # Most recent intent
        
        return analysis
    
    def _detect_current_intent(self, query: str) -> str:
        """Detect the intent of the current query."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['meeting', '회의', '회의록']):
            return "meeting_search"
        elif any(word in query_lower for word in ['when', '언제', 'date', '날짜']):
            return "temporal_query"
        elif any(word in query_lower for word in ['who', '누구', 'attendee', '참석자']):
            return "people_query"
        elif any(word in query_lower for word in ['what', '뭐', 'decision', '결정']):
            return "content_query"
        elif any(word in query_lower for word in ['risk', '리스크', 'investment', '투자']):
            return "financial_query"
        else:
            return "general_query"
    
    def _generate_conversation_summary(self, history: List[Dict[str, Any]]) -> str:
        """
        Generate a summary of the conversation history.
        
        Args:
            history: List of conversation messages
            
        Returns:
            A summary string of the conversation
        """
        if not history:
            return ""
        
        # For a simple approach, just concatenate the last few turns
        summary_parts = []
        
        # Include up to the last 3 turns (user + assistant pairs)
        for msg in history[-min(6, len(history)):]:
            role = msg["role"]
            content = msg["content"]
            
            # Truncate very long messages
            if len(content) > 100:
                content = content[:97] + "..."
            
            summary_parts.append(f"{role.capitalize()}: {content}")
        
        return "\n".join(summary_parts)
    
    def _trim_history(self, session_id: str) -> None:
        """
        Trim the conversation history to the maximum length.
        
        Args:
            session_id: Unique identifier for the conversation
        """
        if session_id in self._conversations:
            history = self._conversations[session_id]["history"]
            if len(history) > self._max_history_length:
                # Keep the most recent messages
                self._conversations[session_id]["history"] = history[-self._max_history_length:]
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear a conversation session.
        
        Args:
            session_id: Unique identifier for the conversation
            
        Returns:
            True if the session was cleared, False if it didn't exist
        """
        if session_id in self._conversations:
            del self._conversations[session_id]
            return True
        return False
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all conversation sessions.
        
        Returns:
            Dictionary of all sessions with their metadata
        """
        # Return a copy with minimal metadata to avoid exposing full history
        sessions = {}
        for session_id, data in self._conversations.items():
            sessions[session_id] = {
                "created_at": data["created_at"],
                "last_updated": data["last_updated"],
                "message_count": len(data["history"])
            }
        return sessions

    def _init_database(self):
        """Initialize SQLite database for conversation persistence."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create conversations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        session_id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        last_updated TEXT NOT NULL,
                        history TEXT NOT NULL,
                        entities TEXT,
                        intents TEXT,
                        document_references TEXT
                    )
                """)
                
                # Create messages table for individual message storage
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        citations TEXT,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY (session_id) REFERENCES conversations (session_id)
                    )
                """)
                
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def _load_conversations_from_db(self):
        """Load conversations from SQLite database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM conversations")
                
                for row in cursor.fetchall():
                    session_id, created_at, last_updated, history_json, entities_json, intents_json, doc_refs_json = row
                    
                    # Parse JSON fields
                    history = json.loads(history_json) if history_json else []
                    entities = json.loads(entities_json) if entities_json else []
                    intents = json.loads(intents_json) if intents_json else []
                    document_references = json.loads(doc_refs_json) if doc_refs_json else []
                    
                    self._conversations[session_id] = {
                        "created_at": created_at,
                        "last_updated": last_updated,
                        "history": history
                    }
                    
                    # Restore tracking data
                    self._entity_tracker[session_id] = entities
                    self._intent_tracker[session_id] = intents
                    self._document_references[session_id] = document_references
                
                logger.info(f"Loaded {len(self._conversations)} conversations from database")
                
        except Exception as e:
            logger.error(f"Failed to load conversations from database: {e}")

    def _save_conversation_to_db(self, session_id: str):
        """Save a single conversation to SQLite database."""
        try:
            if session_id not in self._conversations:
                return
                
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                data = self._conversations[session_id]
                entities = self._entity_tracker.get(session_id, [])
                intents = self._intent_tracker.get(session_id, [])
                document_references = self._document_references.get(session_id, [])
                
                # Insert or update conversation
                cursor.execute("""
                    INSERT OR REPLACE INTO conversations 
                    (session_id, created_at, last_updated, history, entities, intents, document_references)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    data["created_at"],
                    data["last_updated"],
                    json.dumps(data["history"]),
                    json.dumps(entities),
                    json.dumps(intents),
                    json.dumps(document_references)
                ))
                
                conn.commit()
                logger.debug(f"Saved conversation {session_id} to database")
                
        except Exception as e:
            logger.error(f"Failed to save conversation {session_id} to database: {e}")


# Global instance for easy access
conversation_memory = ConversationMemory()
