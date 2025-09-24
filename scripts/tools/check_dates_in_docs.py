#!/usr/bin/env python3
"""
Check all DOCX files for specific date mentions
"""

import os
import docx
from pathlib import Path

def main():
    data_dir = Path('/Users/jinjae/search_agent/data')
    
    for file in os.listdir(data_dir):
        if file.endswith('.docx'):
            print(f'\n=== {file} ===')
            doc = docx.Document(data_dir / file)
            text = '\n'.join([p.text for p in doc.paragraphs][:30])
            print(text[:500] + '...' if len(text) > 500 else text)
            
            # Check for various date formats
            if '8월 2일' in text or 'August 2' in text or '08-02' in text or '2023-08-02' in text:
                print('\n*** FOUND AUGUST 2nd ***')
            
            # Print all date-like patterns
            import re
            date_patterns = [
                r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',  # 2023년 8월 2일
                r'(\d{1,2})월\s*(\d{1,2})일',  # 8월 2일
                r'(\d{4})-(\d{2})-(\d{2})',  # 2023-08-02
                r'다음 회의:\s*(\d{4})-(\d{2})-(\d{2})',  # 다음 회의: 2023-08-02
                r'Date:\s*(\d{4})-(\d{2})-(\d{2})'  # Date: 2023-08-02
            ]
            
            print("\nDates found:")
            for pattern in date_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    for match in matches:
                        if isinstance(match, tuple):
                            if len(match) == 3:
                                if len(match[0]) == 4:  # Year-Month-Day
                                    print(f"  - {match[0]}년 {match[1]}월 {match[2]}일")
                                else:  # Month-Day only
                                    print(f"  - {match[0]}월 {match[1]}일")
                            else:
                                print(f"  - {match}")
                        else:
                            print(f"  - {match}")

if __name__ == "__main__":
    main()
