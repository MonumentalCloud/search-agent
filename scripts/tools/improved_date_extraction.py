#!/usr/bin/env python3
"""
Improved date extraction using LLM
"""

import sys
from pathlib import Path
import json
import datetime
from typing import Optional, Dict, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from configs.load import get_default_llm

def extract_dates_with_llm(text: str) -> Dict[str, Any]:
    """
    Extract dates from text using LLM.
    
    Args:
        text: The text to extract dates from
        
    Returns:
        Dictionary with extracted dates and their context
    """
    llm = get_default_llm()
    
    # Create the prompt for the LLM
    prompt = f"""
You are an expert at analyzing text and extracting date information. 
Extract ALL dates mentioned in the following text, paying special attention to meeting dates, event dates, and document dates.

IMPORTANT RULES:
1. Look for dates in various formats (YYYY-MM-DD, MM/DD/YYYY, Korean format like YYYY년 MM월 DD일, etc.)
2. Pay special attention to phrases like "일시", "날짜", "Date:", "다음 회의:", etc. that indicate dates
3. For each date found, identify its context (e.g., "meeting date", "document date", "next meeting", etc.)
4. Always normalize dates to ISO format (YYYY-MM-DD)

Return a JSON object with the following structure:
{{
  "primary_date": "YYYY-MM-DD",  // The most important date in the document (meeting date, event date)
  "primary_date_context": "brief explanation of what this date represents",
  "all_dates": [
    {{
      "date": "YYYY-MM-DD",
      "context": "explanation of what this date represents",
      "original_text": "the original text snippet containing the date"
    }},
    ...
  ]
}}

Text:
{text[:2000]}  // Truncate to first 2000 chars for LLM context window
"""
    
    try:
        response = llm(prompt)
        
        # Parse the JSON response
        try:
            # Find JSON in the response
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without markdown formatting
                json_match = re.search(r'({.*})', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response
            
            # Clean up the JSON string
            json_str = json_str.strip()
            if json_str.startswith('```') and json_str.endswith('```'):
                json_str = json_str[3:-3].strip()
                
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response: {response}")
            return {"primary_date": None, "all_dates": []}
            
    except Exception as e:
        print(f"Error extracting dates with LLM: {e}")
        return {"primary_date": None, "all_dates": []}

def main():
    """Test the improved date extraction on DOCX files"""
    import docx
    import os
    
    data_dir = Path('/Users/jinjae/search_agent/data')
    
    for file in os.listdir(data_dir):
        if file.endswith('.docx'):
            print(f'\n=== {file} ===')
            doc = docx.Document(data_dir / file)
            text = '\n'.join([p.text for p in doc.paragraphs][:30])
            
            # Extract dates using LLM
            dates = extract_dates_with_llm(text)
            print(f"Primary date: {dates.get('primary_date')}")
            print(f"Primary date context: {dates.get('primary_date_context')}")
            print("All dates:")
            for date_info in dates.get('all_dates', []):
                print(f"  - {date_info.get('date')} ({date_info.get('context')}): {date_info.get('original_text')}")

if __name__ == "__main__":
    import re  # Import here to avoid scope issues
    main()
