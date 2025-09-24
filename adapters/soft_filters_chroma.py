"""
Soft filter implementation for Chroma queries.

This module provides functions to implement soft filters that can adapt to different
data formats and handle failures gracefully by trying alternative formats.
"""

import logging
import re
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

logger = logging.getLogger(__name__)

class SoftFilter:
    """
    A filter that can adapt to different data formats and handle failures gracefully.
    """
    
    @staticmethod
    def create_date_filter(field: str, value: Any, operator: str = "equal") -> List[Dict]:
        """
        Create a date filter that tries multiple formats.
        
        Args:
            field: The field to filter on
            value: The date value (can be string, datetime, etc.)
            operator: The operator to use (equal, greater_than, less_than, etc.)
            
        Returns:
            A list of alternative filter configurations to try
        """
        alternatives = []
        
        # If value is already a datetime object, convert to string
        if isinstance(value, datetime):
            iso_format = value.isoformat()
            alternatives.append({
                "field": field,
                "value": iso_format,
                "operator": operator
            })
            return alternatives
        
        # If value is a string, try to parse it in different formats
        if isinstance(value, str):
            # Try to extract year, month, day
            year_month_day = re.search(r'(\d{4})[년\-]?\s*(\d{1,2})[월\-]?\s*(\d{1,2})[일]?', value)
            if year_month_day:
                year, month, day = year_month_day.groups()
                # Format as ISO date
                iso_format = f"{year}-{int(month):02d}-{int(day):02d}T00:00:00"
                alternatives.append({
                    "field": field,
                    "value": iso_format,
                    "operator": operator
                })
                
                # Also try just the date part
                date_only = f"{year}-{int(month):02d}-{int(day):02d}"
                alternatives.append({
                    "field": field,
                    "value": date_only,
                    "operator": operator
                })
                
                return alternatives
            
            # Try to extract month and day only
            month_day = re.search(r'(\d{1,2})[월\-]?\s*(\d{1,2})[일]?', value)
            if month_day:
                month, day = month_day.groups()
                # Use current year
                current_year = datetime.now().year
                
                # Format as ISO date
                iso_format = f"{current_year}-{int(month):02d}-{int(day):02d}T00:00:00"
                alternatives.append({
                    "field": field,
                    "value": iso_format,
                    "operator": operator
                })
                
                # Also try just the date part
                date_only = f"{current_year}-{int(month):02d}-{int(day):02d}"
                alternatives.append({
                    "field": field,
                    "value": date_only,
                    "operator": operator
                })
                
                return alternatives
            
            # Try to extract month only
            month_only = re.search(r'(\d{1,2})월', value)
            if month_only:
                month = month_only.group(1)
                # Use current year
                current_year = datetime.now().year
                
                # For month-only queries, we'll use greater_than_equal for the start of the month
                # and less_than_equal for the end of the month
                if operator in ["equal", "greater_than_equal", "less_than_equal"]:
                    # Start of month
                    start_of_month = f"{current_year}-{int(month):02d}-01T00:00:00"
                    alternatives.append({
                        "field": field,
                        "value": start_of_month,
                        "operator": "greater_than_equal"
                    })
                    
                    # End of month (simplified to last day of month)
                    if int(month) == 12:
                        next_year = current_year + 1
                        end_of_month = f"{next_year}-01-01T00:00:00"
                    else:
                        end_of_month = f"{current_year}-{int(month)+1:02d}-01T00:00:00"
                    
                    alternatives.append({
                        "field": field,
                        "value": end_of_month,
                        "operator": "less_than"
                    })
                    
                    return alternatives
        
        # If we couldn't parse the value, just return it as is
        alternatives.append({
            "field": field,
            "value": value,
            "operator": operator
        })
        
        return alternatives
    
    @staticmethod
    def apply_filter_alternatives(collection, alternatives: List[Dict]) -> List[Dict]:
        """
        Apply filter alternatives until one succeeds.
        
        Args:
            collection: The Chroma collection object
            alternatives: List of filter alternatives to try
            
        Returns:
            The query result or empty list if all alternatives failed
        """
        for alt in alternatives:
            try:
                field = alt["field"]
                value = alt["value"]
                operator = alt["operator"]
                
                # Build where filter based on operator
                where_filter = {}
                if operator == "equal":
                    where_filter[field] = value
                elif operator == "greater_than":
                    where_filter[f"{field}$gt"] = value
                elif operator == "greater_than_equal":
                    where_filter[f"{field}$gte"] = value
                elif operator == "less_than":
                    where_filter[f"{field}$lt"] = value
                elif operator == "less_than_equal":
                    where_filter[f"{field}$lte"] = value
                else:
                    logger.warning(f"Unsupported operator: {operator}")
                    continue
                
                # Execute the query with this filter
                result = collection.get(
                    where=where_filter,
                    include=["metadatas", "documents"]
                )
                
                # If we got results, return them
                if result and 'ids' in result and result['ids'] and len(result['ids']) > 0:
                    logger.info(f"Filter succeeded with: {alt}")
                    
                    # Process results
                    processed_results = []
                    for i, doc_id in enumerate(result['ids']):
                        if i < len(result['metadatas']) and result['metadatas']:
                            metadata = result['metadatas'][i]
                            document = result['documents'][i] if 'documents' in result and result['documents'] and i < len(result['documents']) else ""
                            
                            # Parse entities from JSON string
                            entities = []
                            if 'entities' in metadata and metadata['entities']:
                                try:
                                    entities = json.loads(metadata['entities'])
                                except:
                                    pass
                            
                            processed_results.append({
                                "chunk_id": doc_id,
                                "doc_id": metadata.get("doc_id", ""),
                                "section": metadata.get("section", ""),
                                "body": document,
                                "entities": entities,
                                "valid_from": metadata.get("valid_from", ""),
                                "valid_to": metadata.get("valid_to", ""),
                                "metadata": {
                                    "section": metadata.get("section", ""),
                                    "entities": entities,
                                    "valid_from": metadata.get("valid_from", ""),
                                    "valid_to": metadata.get("valid_to", ""),
                                }
                            })
                    
                    return processed_results
                
                logger.info(f"Filter returned no results: {alt}")
            
            except Exception as e:
                logger.warning(f"Filter failed: {alt}, error: {e}")
        
        # If all alternatives failed, return empty list
        return []
    
    @staticmethod
    def build_dynamic_filter(facets: Dict[str, Any]) -> List[Dict]:
        """
        Build a list of filter alternatives based on facets.
        
        Args:
            facets: Dictionary of facets from the planner
            
        Returns:
            List of filter alternatives to try
        """
        alternatives = []
        
        # Handle date facets
        if "valid_from" in facets:
            date_alternatives = SoftFilter.create_date_filter(
                field="valid_from", 
                value=facets["valid_from"]
            )
            alternatives.extend(date_alternatives)
        
        # Handle other facet types
        for key, value in facets.items():
            if key != "valid_from":  # Skip date facets already handled
                alternatives.append({
                    "field": key,
                    "value": value,
                    "operator": "equal"
                })
        
        return alternatives


def apply_soft_filters(collection, query: str, facets: Dict[str, Any], alpha: float = 0.5, limit: int = 10) -> List[Dict]:
    """
    Apply soft filters to a hybrid search query.
    
    Args:
        collection: Chroma collection
        query: Search query string
        facets: Dictionary of facets to filter on
        alpha: Hybrid search alpha parameter (not used in Chroma, kept for compatibility)
        limit: Maximum number of results to return
        
    Returns:
        List of search results
    """
    logger.info(f"Applying soft filters with query: '{query}', facets: {facets}, limit: {limit}")
    
    # If no facets, just execute a regular query
    if not facets:
        try:
            # Generate query vector
            from configs.load import get_default_embeddings
            embeddings_model = get_default_embeddings()
            query_vector = embeddings_model.embed_query(query)
            
            logger.info(f"Executing vector search with query: '{query}'")
            
            # Perform vector search
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=limit,
                include=["metadatas", "documents"]
            )
            
            # Process results
            processed_results = []
            try:
                if results and 'ids' in results and results['ids']:
                    # Log the structure of the results for debugging
                    logger.info(f"Vector search returned results with keys: {list(results.keys())}")
                    
                    # Check if ids is a list of lists or just a list
                    if isinstance(results['ids'], list):
                        if len(results['ids']) > 0:
                            if isinstance(results['ids'][0], list):
                                # Structure is [['id1', 'id2', ...]]
                                logger.info(f"Vector search returned {len(results['ids'][0])} results (nested list)")
                                ids_list = results['ids'][0]
                                metadatas_list = results['metadatas'][0] if 'metadatas' in results and results['metadatas'] and len(results['metadatas']) > 0 else []
                                documents_list = results['documents'][0] if 'documents' in results and results['documents'] and len(results['documents']) > 0 else []
                                distances_list = results['distances'][0] if 'distances' in results and results['distances'] and len(results['distances']) > 0 else []
                            else:
                                # Structure is ['id1', 'id2', ...]
                                logger.info(f"Vector search returned {len(results['ids'])} results (flat list)")
                                ids_list = results['ids']
                                metadatas_list = results['metadatas'] if 'metadatas' in results and results['metadatas'] else []
                                documents_list = results['documents'] if 'documents' in results and results['documents'] else []
                                distances_list = results['distances'] if 'distances' in results and results['distances'] else []
                            
                            # Process each result
                            for i, doc_id in enumerate(ids_list):
                                if i < len(metadatas_list):
                                    metadata = metadatas_list[i]
                                    document = documents_list[i] if i < len(documents_list) else ""
                                    
                                    # Parse entities from JSON string
                                    entities = []
                                    if metadata and 'entities' in metadata and metadata['entities']:
                                        try:
                                            entities = json.loads(metadata['entities'])
                                        except Exception as e:
                                            logger.warning(f"Failed to parse entities JSON: {e}")
                                    
                                    # Calculate score
                                    score = 0.0
                                    if i < len(distances_list):
                                        score = distances_list[i]
                                    
                                    processed_results.append({
                                        "chunk_id": doc_id,
                                        "doc_id": metadata.get("doc_id", "") if metadata else "",
                                        "section": metadata.get("section", "") if metadata else "",
                                        "body": document,
                                        "entities": entities,
                                        "valid_from": metadata.get("valid_from", "") if metadata else "",
                                        "valid_to": metadata.get("valid_to", "") if metadata else "",
                                        "score": score,
                                        "metadata": {
                                            "section": metadata.get("section", "") if metadata else "",
                                            "entities": entities,
                                            "valid_from": metadata.get("valid_from", "") if metadata else "",
                                            "valid_to": metadata.get("valid_to", "") if metadata else "",
                                            "meeting_date": metadata.get("meeting_date", "") if metadata else "",
                                            "topic": metadata.get("topic", "") if metadata else "",
                                            "location": metadata.get("location", "") if metadata else "",
                                            "attendees": metadata.get("attendees", "") if metadata else "",
                                        }
                                    })
                
                logger.info(f"Processed {len(processed_results)} results")
                return processed_results
                
            except Exception as e:
                logger.error(f"Error processing results: {e}", exc_info=True)
                return []
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    # Build filter alternatives
    filter_alternatives = SoftFilter.build_dynamic_filter(facets)
    
    # Apply filters
    results = SoftFilter.apply_filter_alternatives(collection, filter_alternatives)
    
    # If all filters failed, try without filters
    if not results:
        logger.warning("All filters failed, trying without filters")
        try:
            # Generate query vector
            from configs.load import get_default_embeddings
            embeddings_model = get_default_embeddings()
            query_vector = embeddings_model.embed_query(query)
            
            # Perform vector search
            chroma_results = collection.query(
                query_embeddings=[query_vector],
                n_results=limit,
                include=["metadatas", "documents"]
            )
            
            # Process results
            results = []
            try:
                if chroma_results and 'ids' in chroma_results and chroma_results['ids']:
                    # Log the structure of the results for debugging
                    logger.info(f"Fallback vector search returned results with keys: {list(chroma_results.keys())}")
                    
                    # Check if ids is a list of lists or just a list
                    if isinstance(chroma_results['ids'], list):
                        if len(chroma_results['ids']) > 0:
                            if isinstance(chroma_results['ids'][0], list):
                                # Structure is [['id1', 'id2', ...]]
                                logger.info(f"Fallback vector search returned {len(chroma_results['ids'][0])} results (nested list)")
                                ids_list = chroma_results['ids'][0]
                                metadatas_list = chroma_results['metadatas'][0] if 'metadatas' in chroma_results and chroma_results['metadatas'] and len(chroma_results['metadatas']) > 0 else []
                                documents_list = chroma_results['documents'][0] if 'documents' in chroma_results and chroma_results['documents'] and len(chroma_results['documents']) > 0 else []
                                distances_list = chroma_results['distances'][0] if 'distances' in chroma_results and chroma_results['distances'] and len(chroma_results['distances']) > 0 else []
                            else:
                                # Structure is ['id1', 'id2', ...]
                                logger.info(f"Fallback vector search returned {len(chroma_results['ids'])} results (flat list)")
                                ids_list = chroma_results['ids']
                                metadatas_list = chroma_results['metadatas'] if 'metadatas' in chroma_results and chroma_results['metadatas'] else []
                                documents_list = chroma_results['documents'] if 'documents' in chroma_results and chroma_results['documents'] else []
                                distances_list = chroma_results['distances'] if 'distances' in chroma_results and chroma_results['distances'] else []
                            
                            # Process each result
                            for i, doc_id in enumerate(ids_list):
                                if i < len(metadatas_list):
                                    metadata = metadatas_list[i]
                                    document = documents_list[i] if i < len(documents_list) else ""
                                    
                                    # Parse entities from JSON string
                                    entities = []
                                    if metadata and 'entities' in metadata and metadata['entities']:
                                        try:
                                            entities = json.loads(metadata['entities'])
                                        except Exception as e:
                                            logger.warning(f"Failed to parse entities JSON: {e}")
                                    
                                    # Calculate score
                                    score = 0.0
                                    if i < len(distances_list):
                                        score = distances_list[i]
                                    
                                    results.append({
                                        "chunk_id": doc_id,
                                        "doc_id": metadata.get("doc_id", "") if metadata else "",
                                        "section": metadata.get("section", "") if metadata else "",
                                        "body": document,
                                        "entities": entities,
                                        "valid_from": metadata.get("valid_from", "") if metadata else "",
                                        "valid_to": metadata.get("valid_to", "") if metadata else "",
                                        "score": score,
                                        "metadata": {
                                            "section": metadata.get("section", "") if metadata else "",
                                            "entities": entities,
                                            "valid_from": metadata.get("valid_from", "") if metadata else "",
                                            "valid_to": metadata.get("valid_to", "") if metadata else "",
                                            "meeting_date": metadata.get("meeting_date", "") if metadata else "",
                                            "topic": metadata.get("topic", "") if metadata else "",
                                            "location": metadata.get("location", "") if metadata else "",
                                            "attendees": metadata.get("attendees", "") if metadata else "",
                                        }
                                    })
                    
                    logger.info(f"Processed {len(results)} fallback results")
                
            except Exception as e:
                logger.error(f"Error processing fallback results: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Fallback query failed: {e}")
    
    return results
