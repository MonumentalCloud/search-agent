"""
Soft filter implementation for Weaviate queries.

This module provides functions to implement soft filters that can adapt to different
data formats and handle failures gracefully by trying alternative formats.
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

from weaviate.collections.classes.filters import Filter

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
                # Format as RFC3339 date
                iso_format = f"{year}-{int(month):02d}-{int(day):02d}T00:00:00Z"
                alternatives.append({
                    "field": field,
                    "value": iso_format,
                    "operator": operator
                })
                
                # Also try without Z
                iso_format_no_z = f"{year}-{int(month):02d}-{int(day):02d}T00:00:00"
                alternatives.append({
                    "field": field,
                    "value": iso_format_no_z,
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
                
                # Format as RFC3339 date
                iso_format = f"{current_year}-{int(month):02d}-{int(day):02d}T00:00:00Z"
                alternatives.append({
                    "field": field,
                    "value": iso_format,
                    "operator": operator
                })
                
                # Also try without Z
                iso_format_no_z = f"{current_year}-{int(month):02d}-{int(day):02d}T00:00:00"
                alternatives.append({
                    "field": field,
                    "value": iso_format_no_z,
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
                    start_of_month = f"{current_year}-{int(month):02d}-01T00:00:00Z"
                    alternatives.append({
                        "field": field,
                        "value": start_of_month,
                        "operator": "greater_than_equal"
                    })
                    
                    # End of month (simplified to last day of month)
                    if int(month) == 12:
                        next_year = current_year + 1
                        end_of_month = f"{next_year}-01-01T00:00:00Z"
                    else:
                        end_of_month = f"{current_year}-{int(month)+1:02d}-01T00:00:00Z"
                    
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
    def apply_filter_alternatives(collection_query, alternatives: List[Dict]) -> Any:
        """
        Apply filter alternatives until one succeeds.
        
        Args:
            collection_query: The Weaviate collection query object
            alternatives: List of filter alternatives to try
            
        Returns:
            The query result or None if all alternatives failed
        """
        for alt in alternatives:
            try:
                field = alt["field"]
                value = alt["value"]
                operator = alt["operator"]
                
                # Apply the filter based on the operator
                if operator == "equal":
                    filter_obj = Filter.by_property(field).equal(value)
                elif operator == "greater_than":
                    filter_obj = Filter.by_property(field).greater_than(value)
                elif operator == "greater_than_equal":
                    filter_obj = Filter.by_property(field).greater_than_equal(value)
                elif operator == "less_than":
                    filter_obj = Filter.by_property(field).less_than(value)
                elif operator == "less_than_equal":
                    filter_obj = Filter.by_property(field).less_than_equal(value)
                else:
                    logger.warning(f"Unsupported operator: {operator}")
                    continue
                
                # Execute the query with this filter
                result = collection_query.with_where(filter_obj).do()
                
                # If we got results, return them
                if result and hasattr(result, "objects") and len(result.objects) > 0:
                    logger.info(f"Filter succeeded with: {alt}")
                    return result
                
                logger.info(f"Filter returned no results: {alt}")
            
            except Exception as e:
                logger.warning(f"Filter failed: {alt}, error: {e}")
        
        # If all alternatives failed, return None
        return None
    
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
        collection: Weaviate collection
        query: Search query string
        facets: Dictionary of facets to filter on
        alpha: Hybrid search alpha parameter
        limit: Maximum number of results to return
        
    Returns:
        List of search results
    """
    # Create base query
    collection_query = collection.query.hybrid(
        query=query,
        alpha=alpha,
        limit=limit
    )
    
    # If no facets, just execute the query
    if not facets:
        result = collection_query.do()
        if result and hasattr(result, "objects"):
            return [obj.properties for obj in result.objects]
        return []
    
    # Build filter alternatives
    filter_alternatives = SoftFilter.build_dynamic_filter(facets)
    
    # Apply filters
    result = SoftFilter.apply_filter_alternatives(collection_query, filter_alternatives)
    
    # If all filters failed, try without filters
    if not result:
        logger.warning("All filters failed, trying without filters")
        result = collection_query.do()
    
    # Extract and return results
    if result and hasattr(result, "objects"):
        return [obj.properties for obj in result.objects]
    
    return []
