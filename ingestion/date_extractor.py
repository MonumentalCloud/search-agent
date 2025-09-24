"""
Date Extraction Module

This module provides functionality to extract dates from text and categorize them.
"""

import re
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from configs.load import get_default_llm

logger = logging.getLogger(__name__)


class DateExtractor:
    """Extract and categorize dates from text."""
    
    def __init__(self):
        self.llm = get_default_llm()
    
    def extract_dates(self, text: str) -> Dict[str, str]:
        """
        Extract dates from text and categorize them.
        
        Args:
            text: The text to extract dates from
            
        Returns:
            Dictionary with date types as keys and ISO format dates as values
        """
        # First try LLM-based extraction
        llm_dates = self._llm_extract_dates(text)
        
        # If LLM extraction fails or returns no dates, fall back to regex
        if not llm_dates:
            regex_dates = self._regex_extract_dates(text)
            return regex_dates
        
        return llm_dates
    
    def _llm_extract_dates(self, text: str) -> Dict[str, str]:
        """Extract dates using LLM."""
        try:
            prompt = f"""
You are an expert at extracting and categorizing dates from text. Analyze the following text and identify all dates mentioned.
For each date, determine its type/category based on context. Pay special attention to meeting-related documents:

IMPORTANT CONTEXT RULES:
- For meeting minutes (회의록): Look for the date when the meeting actually took place, NOT future meeting dates
- "meeting_date" should be the date of the meeting being documented
- "next_meeting_date" or "followup_date" should be for future meetings
- "due_date" for deadlines and action items
- "start_date"/"end_date" for project timelines

Return your answer as a JSON object where keys are date categories and values are ISO format dates (YYYY-MM-DD):
{{
  "meeting_date": "2025-08-11",  // The actual meeting date being documented
  "next_meeting_date": "2025-08-25",  // Future meetings
  "due_date": "2025-09-01",
  ...
}}

If a date is mentioned without a year, assume the current year (2025).
If no dates are found, return an empty object {{}}.

Text:
{text[:2000]}
"""
            response = self.llm.invoke(prompt)
            
            # Try to parse JSON response
            import re, json
            try:
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    if isinstance(result, dict):
                        # Validate dates are in ISO format
                        validated_dates = {}
                        for key, value in result.items():
                            if isinstance(value, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', value):
                                validated_dates[key] = value
                        return validated_dates
            except json.JSONDecodeError:
                pass
            
            # If we couldn't parse JSON or no dates were found, return empty dict
            return {}
            
        except Exception as e:
            logger.warning(f"LLM date extraction failed: {e}")
            return {}
    
    def _regex_extract_dates(self, text: str) -> Dict[str, str]:
        """Extract dates using regex patterns."""
        dates = {}
        
        # Pattern for dates like YYYY-MM-DD, YYYY년 MM월 DD일, MM월 DD일
        date_patterns = [
            (r'(\d{4})[년\-]?\s*(\d{1,2})[월\-]?\s*(\d{1,2})[일]?', 'full_date'),  # YYYY년 MM월 DD일 or YYYY-MM-DD
            (r'(\d{1,2})[월\-]?\s*(\d{1,2})[일]?', 'month_day'),  # MM월 DD일
        ]
        
        # Context patterns to categorize dates
        context_categories = [
            (r'회의|미팅|meeting', 'meeting_date'),
            (r'마감|기한|due|deadline', 'due_date'),
            (r'시작|start|begin', 'start_date'),
            (r'종료|end|finish', 'end_date'),
            (r'발행|publish|publication', 'publication_date'),
            (r'계약|contract', 'contract_date'),
        ]
        
        # Extract full dates (YYYY-MM-DD)
        for match in re.finditer(date_patterns[0][0], text):
            year, month, day = match.groups()
            date_str = f"{year}-{int(month):02d}-{int(day):02d}"
            
            # Get context around the date (50 chars before and after)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end]
            
            # Determine category based on context
            category = 'date'  # Default category
            for pattern, cat in context_categories:
                if re.search(pattern, context):
                    category = cat
                    break
            
            # Add to dates dict, avoiding duplicates
            if category not in dates:
                dates[category] = date_str
        
        # Extract month-day patterns (MM월 DD일) if we don't have many dates yet
        if len(dates) < 2:
            current_year = datetime.now().year
            for match in re.finditer(date_patterns[1][0], text):
                month, day = match.groups()
                date_str = f"{current_year}-{int(month):02d}-{int(day):02d}"
                
                # Get context around the date
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                # Determine category based on context
                category = 'date'  # Default category
                for pattern, cat in context_categories:
                    if re.search(pattern, context):
                        category = cat
                        break
                
                # Add to dates dict, avoiding duplicates
                if category not in dates:
                    dates[category] = date_str
        
        return dates


# Singleton instance for reuse
date_extractor = DateExtractor()


def extract_dates_from_text(text: str) -> Dict[str, str]:
    """
    Extract dates from text and categorize them.
    
    Args:
        text: The text to extract dates from
        
    Returns:
        Dictionary with date types as keys and ISO format dates as values
    """
    return date_extractor.extract_dates(text)
