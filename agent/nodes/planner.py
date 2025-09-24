import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional
from langchain.tools import tool
from langchain_core.language_models import BaseLanguageModel

from configs.load import get_default_llm

logger = logging.getLogger(__name__)


@tool
def search_knowledge_base(query: str, filters: Dict = None) -> str:
    """Search the knowledge base for relevant information."""
    # Placeholder implementation
    return f"Search results for: {query}"


def plan(query: str, lang: str | None, time_hint: str | None, llm: Optional[BaseLanguageModel] = None) -> Dict:
    """Plan the search strategy using LLM."""
    llm = llm or get_default_llm()
    
    # Create prompt directly
    prompt = f"""
    You are a search planner. Analyze the query and create a search plan.
    
    Query: {query}
    Language: {lang or "ko"}
    Time Hint: {time_hint or "none"}
    
    Return a JSON response with:
    - intent: the type of query (legal, how-to, definition, etc.)
    - entities: list of key entities
    - time_hint: temporal context
    - alpha: search parameter (0.25-0.6)
    - facet_sets: list of facet combinations to search
    
    Return only valid JSON.
    """
    
    # Bind tool and get response
    llm_with_tools = llm.bind_tools([search_knowledge_base])
    
    try:
        response = llm_with_tools.invoke(prompt)
        
        # Extract JSON from response
        if hasattr(response, 'content'):
            content = response.content
        else:
            content = str(response)
        
        logger.debug(f"Planner LLM response: {content}")
        
        # Try to parse JSON
        try:
            # Clean up the content to extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"JSON parsing failed: {e}, content: {content}")
            # Fallback to simple parsing
            result = {
                "intent": "general",
                "entities": [query],
                "time_hint": time_hint,
                "alpha": 0.5,
                "facet_sets": [{"doc_type": "document"}]
            }
        
        # Process date facets to ensure they're in the correct format
        if "facet_sets" in result:
            for facet_set in result["facet_sets"]:
                # Check for date fields
                if "date" in facet_set:
                    date_value = facet_set["date"]
                    # Check if it's a Korean date format like "2023년 8월 11일" or "8월 11일"
                    # Check if the date value already has a year
                    import re
                    year_pattern = re.compile(r'^(\d{4})-')
                    year_match = year_pattern.match(date_value)
                    
                    if year_match:
                        # Already in YYYY-MM-DD format, use as is
                        facet_set["valid_from"] = f"{date_value}T00:00:00"
                        del facet_set["date"]
                        continue
                        
                    year_month_day = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', date_value)
                    if year_month_day:
                        year, month, day = year_month_day.groups()
                        # Format as RFC3339 date
                        facet_set["valid_from"] = f"{year}-{int(month):02d}-{int(day):02d}T00:00:00"
                        del facet_set["date"]
                    else:
                        # Check for month-day pattern like "8월 11일"
                        month_day = re.search(r'(\d{1,2})월\s*(\d{1,2})일', date_value)
                        if month_day:
                            month, day = month_day.groups()
                            # Use current year
                            from datetime import datetime
                            current_year = datetime.now().year
                            # Format as RFC3339 date
                            facet_set["valid_from"] = f"{current_year}-{int(month):02d}-{int(day):02d}T00:00:00"
                            del facet_set["date"]
        
        logger.info(f"Planner result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Planner error: {e}")
        return {
            "intent": "general",
            "entities": [query],
            "time_hint": time_hint,
            "alpha": 0.5,
            "facet_sets": [{"doc_type": "document"}]
        }
