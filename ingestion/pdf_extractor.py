import logging
import os
from typing import Dict, List, Optional
from pathlib import Path

try:
    import PyPDF2
    import pdfplumber
except ImportError:
    PyPDF2 = None
    pdfplumber = None

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str, method: str = "pdfplumber") -> Dict[str, any]:
    """Extract text from PDF file with metadata."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    file_name = Path(file_path).stem
    file_size = os.path.getsize(file_path)
    
    try:
        if method == "pdfplumber" and pdfplumber:
            return _extract_with_pdfplumber(file_path, file_name, file_size)
        elif method == "PyPDF2" and PyPDF2:
            return _extract_with_pypdf2(file_path, file_name, file_size)
        else:
            raise ImportError(f"PDF extraction library not available: {method}")
    except Exception as e:
        logger.error(f"Failed to extract text from {file_path}: {e}")
        raise


def _extract_with_pdfplumber(file_path: str, file_name: str, file_size: int) -> Dict[str, any]:
    """Extract text using pdfplumber (better for complex layouts)."""
    text_parts = []
    page_count = 0
    
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(f"=== Page {page_num} ===\n{page_text.strip()}")
                    page_count += 1
            except Exception as e:
                logger.warning(f"Failed to extract page {page_num}: {e}")
                continue
    
    full_text = "\n\n".join(text_parts)
    
    return {
        "file_name": file_name,
        "file_path": file_path,
        "file_size": file_size,
        "page_count": page_count,
        "text": full_text,
        "extraction_method": "pdfplumber"
    }


def _extract_with_pypdf2(file_path: str, file_name: str, file_size: int) -> Dict[str, any]:
    """Extract text using PyPDF2 (fallback method)."""
    text_parts = []
    
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        page_count = len(pdf_reader.pages)
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(f"=== Page {page_num} ===\n{page_text.strip()}")
            except Exception as e:
                logger.warning(f"Failed to extract page {page_num}: {e}")
                continue
    
    full_text = "\n\n".join(text_parts)
    
    return {
        "file_name": file_name,
        "file_path": file_path,
        "file_size": file_size,
        "page_count": page_count,
        "text": full_text,
        "extraction_method": "PyPDF2"
    }


def detect_document_type(file_name: str) -> str:
    """Detect document type from filename."""
    file_lower = file_name.lower()
    
    if "감독규정" in file_name or "감독규정시행세칙" in file_name:
        return "regulation"
    elif "개래법" in file_name or "시행령" in file_name:
        return "law"
    elif "가이드" in file_name or "guide" in file_lower:
        return "guide"
    elif "정책" in file_name or "policy" in file_lower:
        return "policy"
    else:
        return "document"


def detect_jurisdiction(file_name: str) -> str:
    """Detect jurisdiction from filename."""
    if any(keyword in file_name for keyword in ["금융감독원", "금융위원회", "대통령령"]):
        return "KR"
    else:
        return "KR"  # Default to Korea for Korean documents


def extract_sections_from_text(text: str) -> List[Dict[str, str]]:
    """Extract sections from text using common document patterns."""
    sections = []
    
    # Common section header patterns
    patterns = [
        # Korean legal document patterns
        r"제\s*\d+\s*조",  # Article X
        r"제\s*\d+\s*장",  # Chapter X
        r"제\s*\d+\s*절",  # Section X
        r"제\s*\d+\s*항",  # Paragraph X
        r"제\s*\d+\s*호",  # Item X
        r"^\s*\d+\.",      # Numbered items
        r"^\s*[가-힣]\.",  # Korean letter items
        
        # English document patterns
        r"^#+\s+.+",       # Markdown headers (# Title)
        r"^Section\s+\d+",  # Section X
        r"^Chapter\s+\d+",  # Chapter X
        r"^Part\s+\d+",     # Part X
        r"^Appendix\s+\w+", # Appendix X
        r"^=== Page \d+ ===" # Page markers
    ]
    
    import re
    
    # First, try to find markdown-style sections (## Section X)
    markdown_sections = re.split(r'(?m)^(#+\s+.+)$', text)
    if len(markdown_sections) > 2:  # Found markdown headers
        current_section = {"heading": "Introduction", "text": "", "order": 0}
        for i, part in enumerate(markdown_sections):
            part = part.strip()
            if not part:
                continue
                
            if re.match(r'^#+\s+.+', part):  # This is a header
                # Save previous section
                if current_section["text"].strip():
                    sections.append(current_section.copy())
                
                # Start new section
                current_section = {
                    "heading": part,
                    "text": "",
                    "order": len(sections) + 1
                }
            else:
                current_section["text"] += part + "\n"
        
        # Add the last section
        if current_section["text"].strip():
            sections.append(current_section)
            
        return sections
    
    # If no markdown headers found, try other patterns
    lines = text.split('\n')
    current_section = {"heading": "Introduction", "text": "", "order": 0}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if line matches a section pattern
        is_section_header = False
        for pattern in patterns:
            if re.match(pattern, line):
                # Save previous section
                if current_section["text"].strip():
                    sections.append(current_section.copy())
                
                # Start new section
                current_section = {
                    "heading": line,
                    "text": "",
                    "order": len(sections) + 1
                }
                is_section_header = True
                break
        
        if not is_section_header:
            current_section["text"] += line + "\n"
    
    # Add the last section
    if current_section["text"].strip():
        sections.append(current_section)
    
    return sections

