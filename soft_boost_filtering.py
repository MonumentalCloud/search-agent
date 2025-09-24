#!/usr/bin/env python3
"""
Soft Boost Filtering System - Your Vision Implemented

This implements the flexible metadata schema system you described:
1. Retrieve large pool of chunks with semantic search (no hard filters)
2. Discover available metadata facets dynamically 
3. Apply soft boosting based on metadata relevance
4. Handle shifting metadata schemas gracefully
"""

import logging
import json
import re
from typing import Dict, List, Any, Tuple, Optional
from collections import Counter
import math

logger = logging.getLogger(__name__)

class SoftBoostFilter:
    """
    A flexible filtering system that uses soft boosting instead of hard filtering.
    Adapts to shifting metadata schemas and handles missing/incomplete data gracefully.
    """
    
    def __init__(self):
        self.boost_weights = {
            'date_match': 1.5,      # Strong boost for date matches
            'partial_date': 1.2,    # Moderate boost for partial date matches
            'day_of_week_match': 2.5,  # Strong boost for day-of-week matches
            'semantic_relevance': 1.0,  # Base semantic relevance
            'metadata_completeness': 1.1,  # Boost for complete metadata
        }
        self.llm = None
    
    def _get_llm_client(self):
        if self.llm is None:
            from configs.load import get_default_llm
            self.llm = get_default_llm()
        return self.llm
    
    def discover_metadata_schema(self, chunks: List[Dict]) -> Dict[str, Any]:
        """
        Dynamically discover what metadata fields are available in the chunk pool.
        This adapts to shifting schemas over time.
        """
        schema = {
            'available_fields': set(),
            'field_types': {},
            'field_examples': {},
            'field_coverage': {}
        }
        
        for chunk in chunks:
            metadata = chunk.get('metadata', {})
            
            for field, value in metadata.items():
                schema['available_fields'].add(field)
                
                # Track field types
                if field not in schema['field_types']:
                    schema['field_types'][field] = set()
                schema['field_types'][field].add(type(value).__name__)
                
                # Track examples (limit to 3 per field)
                if field not in schema['field_examples']:
                    schema['field_examples'][field] = []
                if len(schema['field_examples'][field]) < 3 and value:
                    schema['field_examples'][field].append(str(value)[:50])
                
                # Track coverage
                if field not in schema['field_coverage']:
                    schema['field_coverage'][field] = 0
                if value and str(value).strip():
                    schema['field_coverage'][field] += 1
        
        # Convert coverage to percentages
        total_chunks = len(chunks)
        for field in schema['field_coverage']:
            schema['field_coverage'][field] = schema['field_coverage'][field] / total_chunks
        
        logger.info(f"Discovered metadata schema with {len(schema['available_fields'])} fields")
        logger.info(f"Field coverage: {[(k, f'{v:.1%}') for k, v in schema['field_coverage'].items()]}")
        
        return schema
    
    def extract_query_intent(self, query: str) -> Dict[str, Any]:
        """
        Extract intent from query using LLM for robust understanding.
        """
        llm_client = self._get_llm_client()
        if not llm_client:
            logger.warning("LLM client not available for query intent extraction.")
            return {"dates": [], "entities": [], "day_of_week": []}

        prompt = f"""Analyze this query and extract key information for search filtering.

Query: "{query}"

Extract the following information:
1. Any specific dates mentioned (in YYYY-MM-DD format)
2. Any day-of-week mentions (Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday, or Korean equivalents)
3. Any key entities or topics

Return a JSON object with these fields:
{{
    "dates": ["2025-08-11", "2025-08-15"],
    "day_of_week": ["tuesday", "monday"],
    "entities": ["meetings", "marketing", "회의"],
    "intent": "search_for_tuesday_meetings"
}}

Examples:
- "get me all meetings that happened on tuesday" -> {{"dates": [], "day_of_week": ["tuesday"], "entities": ["meetings"], "intent": "search_for_tuesday_meetings"}}
- "2025년 8월 11일 회의록" -> {{"dates": ["2025-08-11"], "day_of_week": [], "entities": ["회의록"], "intent": "search_for_specific_date"}}
- "화요일에 열린 모든 회의" -> {{"dates": [], "day_of_week": ["tuesday"], "entities": ["회의"], "intent": "search_for_tuesday_meetings"}}
"""

        try:
            response = llm_client.invoke(prompt)
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                logger.info(f"Extracted query intent: {result}")
                return result
        except Exception as e:
            logger.warning(f"Failed to extract query intent with LLM: {e}")
        
        return {"dates": [], "day_of_week": [], "entities": [], "intent": "unknown"}
    
    def calculate_metadata_boost(self, chunk: Dict, query_intent: Dict, schema: Dict) -> float:
        """
        Calculate soft boost score based on metadata relevance to query intent.
        This is the core of your soft boosting vision.
        """
        boost_score = 1.0
        metadata = chunk.get('metadata', {}) or {}
        
        # Date matching boost
        if query_intent.get('dates') and 'meeting_date' in metadata:
            chunk_date = metadata.get('meeting_date', '')
            chunk_valid_from = metadata.get('valid_from', '')
            
            for query_date in query_intent.get('dates', []):
                if self._date_matches(chunk_date, query_date):
                    boost_score *= self.boost_weights['date_match']
                    logger.debug(f"Date match boost: {chunk_date} matches {query_date}")
                elif self._partial_date_matches(chunk_date, query_date):
                    boost_score *= self.boost_weights['partial_date']
                    logger.debug(f"Partial date match boost: {chunk_date} partially matches {query_date}")
                
                if self._date_matches(chunk_valid_from, query_date):
                    boost_score *= self.boost_weights['date_match']
                    logger.debug(f"Valid_from date match boost: {chunk_valid_from} matches {query_date}")
        
        # Day-of-week matching boost
        if 'day_of_week' in query_intent and query_intent['day_of_week']:
            meeting_date = metadata.get('meeting_date', '')
            if meeting_date:
                chunk_day_of_week = self._get_day_of_week(meeting_date)
                for query_day in query_intent['day_of_week']:
                    if chunk_day_of_week and chunk_day_of_week.lower() == query_day.lower():
                        boost_score *= self.boost_weights['day_of_week_match']
                        logger.debug(f"Day-of-week match boost: {chunk_day_of_week} matches {query_day}")
        
        # Time matching boost
        if query_intent.get('has_time') and 'meeting_time' in metadata:
            chunk_time = metadata.get('meeting_time', '')
            for query_time in query_intent.get('time_values', []):
                if self._time_matches(chunk_time, query_time):
                    boost_score *= 1.2  # Moderate boost for time matches
        
        # Entity matching boost
        if query_intent.get('entities'):
            doc_type = metadata.get('doc_type', '').lower()
            topic = metadata.get('topic', '').lower()
            body = chunk.get('body', '').lower()
            
            for entity in query_intent['entities']:
                entity_lower = entity.lower()
                if entity_lower in doc_type or entity_lower in topic or entity_lower in body:
                    boost_score *= 1.3
                    logger.debug(f"Entity match boost: {entity} found in metadata or body")
        
        # Metadata completeness boost
        completeness_score = self._calculate_completeness(metadata, schema)
        boost_score *= (1.0 + (completeness_score * 0.1))  # 10% boost for completeness
        
        return boost_score
    
    def _date_matches(self, chunk_date: str, query_date: str) -> bool:
        """Check if chunk date matches query date (flexible matching)."""
        if not chunk_date or not query_date:
            return False
        
        # Normalize dates
        chunk_normalized = self._normalize_date(chunk_date)
        query_normalized = self._normalize_date(query_date)
        
        return chunk_normalized == query_normalized
    
    def _partial_date_matches(self, chunk_date: str, query_date: str) -> bool:
        """Check for partial date matches (e.g., same month-day)."""
        if not chunk_date or not query_date:
            return False
        
        chunk_normalized = self._normalize_date(chunk_date)
        query_normalized = self._normalize_date(query_date)
        
        # Check if month-day matches (ignore year)
        if len(chunk_normalized) >= 5 and len(query_normalized) >= 5:
            return chunk_normalized[5:] == query_normalized[5:]  # MM-DD part
        
        return False
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to YYYY-MM-DD format."""
        if not date_str:
            return ""
        
        # Extract year, month, day from various formats
        patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # 2025-08-11
            r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',  # 2025년 8월 11일
            r'(\d{1,2})월\s*(\d{1,2})일',  # 8월 11일 (use current year)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                if len(match.groups()) == 3:
                    year, month, day = match.groups()
                    return f"{year}-{int(month):02d}-{int(day):02d}"
                elif len(match.groups()) == 2:
                    month, day = match.groups()
                    # Use current year for month-day only
                    from datetime import datetime
                    current_year = datetime.now().year
                    return f"{current_year}-{int(month):02d}-{int(day):02d}"
        
        return date_str
    
    def _get_day_of_week(self, date_str: str) -> str:
        """Get day of week from date string."""
        if not date_str:
            return ""
        
        try:
            from datetime import datetime
            # Try to parse the date
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            return days[date_obj.weekday()]
        except (ValueError, TypeError):
            return ""
    
    def _time_matches(self, chunk_time: str, query_time: tuple) -> bool:
        """Check if chunk time matches query time."""
        if not chunk_time or not query_time:
            return False
        
        # Simple time matching (could be enhanced)
        return str(query_time[0]) in chunk_time and str(query_time[1]) in chunk_time
    
    def _calculate_completeness(self, metadata: Dict, schema: Dict) -> float:
        """Calculate metadata completeness score."""
        if not schema['available_fields']:
            return 0.0
        
        complete_fields = 0
        total_fields = len(schema['available_fields'])
        
        for field in schema['available_fields']:
            value = metadata.get(field, '')
            if value and str(value).strip():
                complete_fields += 1
        
        return complete_fields / total_fields
    
    def _get_boost_reasons(self, chunk: Dict, query_intent: Dict, schema: Dict) -> List[str]:
        """Get human-readable reasons for boost score changes."""
        reasons = []
        metadata = chunk.get('metadata', {}) or {}
        
        # Check for date matches
        if query_intent.get('dates') and 'meeting_date' in metadata:
            chunk_date = metadata.get('meeting_date', '')
            for query_date in query_intent.get('dates', []):
                if self._date_matches(chunk_date, query_date):
                    reasons.append(f"Exact date match: {chunk_date}")
                elif self._partial_date_matches(chunk_date, query_date):
                    reasons.append(f"Partial date match: {chunk_date}")
        
        # Check for day-of-week matches
        if 'day_of_week' in query_intent and query_intent['day_of_week']:
            meeting_date = metadata.get('meeting_date', '')
            if meeting_date:
                chunk_day_of_week = self._get_day_of_week(meeting_date)
                for query_day in query_intent['day_of_week']:
                    if chunk_day_of_week and chunk_day_of_week.lower() == query_day.lower():
                        reasons.append(f"Day-of-week match: {chunk_day_of_week}")
        
        # Check for entity matches
        if query_intent.get('entities'):
            doc_type = metadata.get('doc_type', '').lower()
            topic = metadata.get('topic', '').lower()
            body = chunk.get('body', '').lower()
            
            for entity in query_intent['entities']:
                entity_lower = entity.lower()
                if entity_lower in doc_type:
                    reasons.append(f"Entity match in doc_type: {entity}")
                elif entity_lower in topic:
                    reasons.append(f"Entity match in topic: {entity}")
                elif entity_lower in body:
                    reasons.append(f"Entity match in content: {entity}")
        
        # Check metadata completeness
        completeness_score = self._calculate_completeness(metadata, schema)
        if completeness_score > 0.8:
            reasons.append("High metadata completeness")
        elif completeness_score < 0.3:
            reasons.append("Low metadata completeness")
        
        return reasons if reasons else ["No specific matches found"]
    
    def apply_soft_boosting(self, chunks: List[Dict], query: str) -> Dict[str, Any]:
        """
        Apply soft boosting to chunks based on query intent and metadata relevance.
        Returns detailed boost information including winners and losers.
        """
        # Discover metadata schema from the chunk pool
        schema = self.discover_metadata_schema(chunks)
        
        # Extract query intent
        query_intent = self.extract_query_intent(query)
        
        logger.info(f"Query intent: {query_intent}")
        
        # Calculate boost scores for each chunk
        boosted_chunks = []
        boost_details = []
        
        for i, chunk in enumerate(chunks):
            # Base semantic score (assume 1.0 for all chunks initially)
            base_score = 1.0
            boost_score = self.calculate_metadata_boost(chunk, query_intent, schema)
            
            # Calculate boost change
            boost_change = boost_score - base_score
            boost_percentage = ((boost_score / base_score) - 1) * 100 if base_score > 0 else 0
            
            boosted_chunks.append((chunk, boost_score))
            
            # Store detailed boost information
            boost_details.append({
                'original_position': i + 1,
                'chunk_id': chunk.get('chunk_id', ''),
                'doc_id': chunk.get('doc_id', ''),
                'meeting_date': chunk.get('metadata', {}).get('meeting_date', 'N/A'),
                'topic': chunk.get('metadata', {}).get('topic', 'N/A'),
                'base_score': base_score,
                'boost_score': boost_score,
                'boost_change': boost_change,
                'boost_percentage': boost_percentage,
                'reasons': self._get_boost_reasons(chunk, query_intent, schema)
            })
        
        # Sort by boost score (highest first)
        boosted_chunks.sort(key=lambda x: x[1], reverse=True)
        
        # Update final positions and find winners/losers
        winners = []
        losers = []
        
        for i, (chunk, boost_score) in enumerate(boosted_chunks):
            final_position = i + 1
            chunk_id = chunk.get('chunk_id', '')
            
            # Find the corresponding boost detail
            boost_detail = next((bd for bd in boost_details if bd['chunk_id'] == chunk_id), None)
            if boost_detail:
                boost_detail['final_position'] = final_position
                position_change = boost_detail['original_position'] - final_position
                boost_detail['position_change'] = position_change
                
                # Categorize as winner or loser
                if boost_detail['boost_change'] > 0.05:  # Significant boost
                    winners.append(boost_detail)
                elif boost_detail['boost_change'] < -0.02:  # Significant loss
                    losers.append(boost_detail)
        
        # Sort winners by boost change (highest first) and losers by boost change (lowest first)
        winners.sort(key=lambda x: x['boost_change'], reverse=True)
        losers.sort(key=lambda x: x['boost_change'])
        
        logger.info(f"Applied soft boosting to {len(chunks)} chunks")
        logger.info(f"Top 3 boost scores: {[f'{x[1]:.2f}' for x in boosted_chunks[:3]]}")
        logger.info(f"Top 3 boosted chunks: {len(winners[:3])}, Bottom 3 debuffed chunks: {len(losers[:3])}")
        
        return {
            'boosted_chunks': boosted_chunks,
            'boost_details': boost_details,
            'winners': winners[:3],  # Top 3 boosted chunks
            'losers': losers[:3],   # Bottom 3 debuffed chunks
            'query_intent': query_intent,
            'schema_info': {
                'total_fields': len(schema['available_fields']),
                'field_coverage': {k: f"{v:.1%}" for k, v in schema['field_coverage'].items()}
            }
        }

def test_soft_boosting():
    """Test the soft boosting system with the 사이버 document."""
    from adapters.chroma_adapter import ChromaClient
    
    # Get some chunks from ChromaDB
    client = ChromaClient()
    collection = client._client.get_collection(client.chunk_collection)
    
    # Get all documents (this would normally be the semantic search results)
    results = collection.get(include=['metadatas', 'documents'])
    
    if not results or 'ids' not in results:
        print("No documents found")
        return
    
    # Convert to our chunk format
    chunks = []
    for i, chunk_id in enumerate(results['ids']):
        metadata = results['metadatas'][i] if 'metadatas' in results else {}
        document = results['documents'][i] if 'documents' in results else ''
        
        chunks.append({
            'chunk_id': chunk_id,
            'metadata': metadata,
            'document': document,
            'doc_id': metadata.get('doc_id', '')
        })
    
    # Test soft boosting
    soft_filter = SoftBoostFilter()
    query = "2025년 8월 11일날 회의록 있어?"
    
    boosted_chunks = soft_filter.apply_soft_boosting(chunks, query)
    
    print(f"Soft boosting results for query: '{query}'")
    print("=" * 60)
    
    for i, (chunk, boost_score) in enumerate(boosted_chunks[:5]):
        metadata = chunk['metadata']
        doc_id = metadata.get('doc_id', 'UNKNOWN')
        meeting_date = metadata.get('meeting_date', 'NO DATE')
        is_saibeo = '사이버' in chunk['document']
        
        print(f"{i+1}. Boost: {boost_score:.2f}")
        print(f"   Doc ID: {doc_id}")
        print(f"   Meeting date: {meeting_date}")
        print(f"   Is 사이버: {is_saibeo}")
        print(f"   Content: {chunk['document'][:50]}...")
        print()

if __name__ == "__main__":
    test_soft_boosting()
