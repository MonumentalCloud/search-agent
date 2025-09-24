#!/usr/bin/env python3
"""
Check dates in DOCX files
"""

import os
import docx
import re
from pathlib import Path
from datetime import datetime

# Directory containing DOCX files
data_dir = Path("data")

def extract_text_from_docx(file_path):
    """Extract text from a DOCX file."""
    try:
        # Load the document
        doc = docx.Document(file_path)
        
        # Extract text from paragraphs
        text = "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return text
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return ""

def find_dates(text):
    """Find dates in text."""
    # Pattern for dates like YYYY-MM-DD, YYYY년 MM월 DD일, MM월 DD일
    date_patterns = [
        r'(\d{4})[년\-]?\s*(\d{1,2})[월\-]?\s*(\d{1,2})[일]?',  # YYYY년 MM월 DD일 or YYYY-MM-DD
        r'(\d{1,2})[월\-]?\s*(\d{1,2})[일]?',                   # MM월 DD일
    ]
    
    dates = []
    
    # Check for full date pattern (YYYY-MM-DD or YYYY년 MM월 DD일)
    for match in re.finditer(date_patterns[0], text):
        year, month, day = match.groups()
        date_str = f"{year}-{int(month):02d}-{int(day):02d}"
        dates.append({
            "date": date_str,
            "match": match.group(0),
            "context": text[max(0, match.start()-50):match.end()+50]
        })
    
    # Check for month-day pattern (MM월 DD일)
    for match in re.finditer(date_patterns[1], text):
        month, day = match.groups()
        current_year = datetime.now().year
        date_str = f"{current_year}-{int(month):02d}-{int(day):02d}"
        
        # Check if this is a duplicate (already found with year)
        duplicate = False
        for existing in dates:
            if existing["date"].endswith(f"-{int(month):02d}-{int(day):02d}"):
                duplicate = True
                break
        
        if not duplicate:
            dates.append({
                "date": date_str,
                "match": match.group(0),
                "context": text[max(0, match.start()-50):match.end()+50]
            })
    
    return dates

# Process all DOCX files
docx_files = list(data_dir.glob("*.docx"))
print(f"Found {len(docx_files)} DOCX files")

for file_path in docx_files:
    print(f"\nProcessing {file_path.name}:")
    text = extract_text_from_docx(file_path)
    dates = find_dates(text)
    
    if dates:
        print(f"  Found {len(dates)} date references:")
        for i, date_info in enumerate(dates):
            print(f"  {i+1}. {date_info['date']} (matched: {date_info['match']})")
            print(f"     Context: ...{date_info['context']}...")
    else:
        print("  No dates found")

# Specifically check for August 2nd (8월 2일)
print("\n\nSpecifically checking for August 2nd (8월 2일):")
for file_path in docx_files:
    text = extract_text_from_docx(file_path)
    
    # Check for 8월 2일 or 8월2일
    if "8월 2일" in text or "8월2일" in text:
        print(f"\nFound in {file_path.name}:")
        
        # Find the context
        for pattern in ["8월 2일", "8월2일"]:
            for match in re.finditer(pattern, text):
                context = text[max(0, match.start()-50):match.end()+50]
                print(f"  Context: ...{context}...")
    
    # Check for 2025-08-02
    if "2025-08-02" in text:
        print(f"\nFound ISO date in {file_path.name}:")
        for match in re.finditer("2025-08-02", text):
            context = text[max(0, match.start()-50):match.end()+50]
            print(f"  Context: ...{context}...")
