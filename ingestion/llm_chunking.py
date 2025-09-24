"""
LLM-Based Chunking and Entity Extraction

This module provides intelligent chunking and entity extraction using LLMs
that understand Korean legal document structure and semantics.
"""

import json
import logging
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from configs.load import get_default_llm

logger = logging.getLogger(__name__)


@dataclass
class ChunkResult:
    """Result of LLM-based chunking."""
    text: str
    entities: List[str]
    chunk_type: str  # e.g., "article", "definition", "provision"
    article_number: Optional[str] = None
    section_title: Optional[str] = None
    token_count: int = 0


class LLMEntityExtractor:
    """LLM-based entity extraction for general documents."""
    def __init__(self):
        self.llm = get_default_llm()
    def extract_entities(self, text: str) -> Dict[str, list]:
        """Extract entities and relationships using LLM. Returns a dict with 'entities' and 'relationships'."""
        def deduplicate_preserve_order(seq):
            seen = set()
            return [x for x in seq if not (x in seen or seen.add(x))]
        try:
            prompt = f"""
You are an expert at analyzing text. Extract all key entities (people, organizations, locations, terms, etc.) and any explicit relationships (who did what to whom, cause-effect, part-of, etc.) present in the following text. Return a JSON object:
{{
  "entities": ["entity1", "entity2", ...],
  "relationships": [
    {{"subject": "...", "relation": "...", "object": "..."}},
    ...
  ]
}}
Text:
{text}
"""
            response = self.llm.invoke(prompt)
            # Try to parse JSON response
            import re, json
            entities = []
            relationships = []
            try:
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    entities = result.get("entities", [])
                    relationships = result.get("relationships", [])
                    entities = deduplicate_preserve_order([str(e).strip() for e in entities if e.strip()])
                    if not isinstance(relationships, list):
                        relationships = []
            except json.JSONDecodeError:
                pass
            # Fallback: extract entities from text response
            if not entities:
                lines = response.content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('{') and not line.startswith('}'):
                        entity = re.sub(r'^[-•*]\s*', '', line)
                        entity = re.sub(r'^"\s*|\s*"$', '', entity)  # Remove quotes
                        if entity and len(entity) > 1:
                            entities.append(entity)
                entities = deduplicate_preserve_order(entities[:10])
            return {"entities": entities, "relationships": relationships}
        except Exception as e:
            logger.warning(f"LLM entity extraction failed: {e}")
            return {"entities": [], "relationships": []}
    
    def _fallback_entity_extraction(self, text: str) -> List[str]:
        """Fallback entity extraction using patterns."""
        entities = []
        
        # Korean legal patterns
        patterns = [
            r'제\d+조',  # Article X
            r'제\d+장',  # Chapter X
            r'제\d+절',  # Section X
            r'제\d+항',  # Paragraph X
            r'[가-힣]+법',  # Law names
            r'[가-힣]+령',  # Decree names
            r'[가-힣]+규정',  # Regulation names
            r'[가-힣]+감독원',  # Supervisory authorities
            r'[가-힣]+위원회',  # Committees
            r'전자금융거래',  # Electronic financial transactions
            r'금융기관',  # Financial institutions
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            entities.extend(matches)
        
        return list(set(entities))  # Remove duplicates


class LLMChunker:
    """LLM-based intelligent chunking for Korean legal documents."""
    
    def __init__(self):
        self.llm = get_default_llm()
        self.entity_extractor = LLMEntityExtractor()
    
    def chunk_text(self, text: str, max_tokens: int = 400) -> List[ChunkResult]:
        """Chunk text using LLM understanding of document structure."""
        try:
            # First, let LLM analyze the document structure
            structure = self._analyze_document_structure(text)
            # Then chunk based on the structure
            chunks = self._chunk_by_structure(text, structure, max_tokens)
            # Extract entities and relationships for each chunk
            for chunk in chunks:
                extraction = self.entity_extractor.extract_entities(chunk.text)
                chunk.entities = extraction["entities"]
                chunk.token_count = len(chunk.text.split()) * 2  # Rough token estimate
                # Store relationships as an attribute if you want to use it downstream
                chunk.relationships = extraction["relationships"]
            return chunks
        except Exception as e:
            logger.warning(f"LLM chunking failed: {e}")
            # Fallback to simple chunking
            return self._fallback_chunking(text, max_tokens)
    
    def _analyze_document_structure(self, text: str) -> Dict:
        """Analyze document structure using LLM."""
        try:
            prompt = f"""
You are an expert at analyzing and segmenting text. Split the following text into coherent, self-contained units of information. Each chunk should represent a complete logical unit (like a section, paragraph, or distinct concept) that is understandable on its own.

IMPORTANT RULES:
1. NEVER split in the middle of sentences or paragraphs.
2. Each section header (like "# Title", "## Section 2:", etc.) should start a new chunk.
3. Make sure each chunk is a complete, coherent unit with proper context.
4. Do not create chunks that start with conjunctions, partial sentences, or other fragments.
5. Ensure that the start_pos and end_pos values are accurate and do not overlap.

For each chunk, provide its start and end character positions and a short summary. Return a JSON object:
{{
  "structure": [
    {{
      "start_pos": <start_index>,
      "end_pos": <end_index>,
      "type": "<section|paragraph|list|other>",
      "title": "<section title if applicable>",
      "summary": "<short summary of the chunk>"
    }},
    ...
  ]
}}

Text:
{text[:2000]}...
"""
            response = self.llm.invoke(prompt)
            # Try to parse JSON
            try:
                import re, json
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result
            except json.JSONDecodeError:
                pass
            # Fallback: simple structure analysis
            return self._simple_structure_analysis(text)
        except Exception as e:
            logger.warning(f"Structure analysis failed: {e}")
            return self._simple_structure_analysis(text)
    
    def _simple_structure_analysis(self, text: str) -> Dict:
        """Simple structure analysis using regex."""
        structure = {"structure": []}
        
        # Find article patterns
        article_pattern = r'제\d+조\s*\([^)]*\)'
        for match in re.finditer(article_pattern, text):
            structure["structure"].append({
                "type": "article",
                "title": match.group(),
                "start_pos": match.start(),
                "end_pos": match.end(),
                "article_number": match.group()
            })
        
        return structure
    
    def _chunk_by_structure(self, text: str, structure: Dict, max_tokens: int) -> List[ChunkResult]:
        """Chunk text based on analyzed structure."""
        chunks = []
        structure_items = structure.get("structure", [])
        
        if not structure_items:
            # No structure found, use paragraph-based chunking
            logger.warning("No structure found in document, falling back to paragraph-based chunking")
            return self._chunk_by_paragraphs(text, max_tokens)
        
        # Log the structure for debugging
        logger.debug(f"Document structure: {structure_items}")
        
        # Sort by position
        structure_items.sort(key=lambda x: x.get("start_pos", 0))
        
        # Process each structure item to create chunks
        for i, item in enumerate(structure_items):
            try:
                # Get the exact start and end positions from the LLM's analysis
                start_pos = int(item.get("start_pos", 0))
                end_pos = int(item.get("end_pos", 0))
                
                # Ensure end_pos is valid
                if end_pos <= 0 or end_pos > len(text):
                    end_pos = len(text)
                    if i + 1 < len(structure_items):
                        next_start = int(structure_items[i + 1].get("start_pos", len(text)))
                        if next_start > start_pos:
                            end_pos = next_start
                
                # Extract the chunk text using the exact positions
                chunk_text = text[start_pos:end_pos].strip()
                
                # Skip empty chunks
                if not chunk_text:
                    logger.warning(f"Empty chunk detected at position {start_pos}:{end_pos}")
                    continue
                
                # Log the chunk for debugging
                logger.debug(f"Chunk {i}: {start_pos}:{end_pos} - '{chunk_text[:50]}...'")
                
                # Create the chunk
                if len(chunk_text.split()) * 2 > max_tokens:
                    # Chunk is too large, split further by paragraphs
                    logger.info(f"Chunk {i} exceeds token limit, splitting further")
                    sub_chunks = self._chunk_by_paragraphs(chunk_text, max_tokens)
                    for sub_chunk in sub_chunks:
                        sub_chunk.article_number = item.get("article_number")
                        sub_chunk.section_title = item.get("title")
                        sub_chunk.chunk_type = item.get("type", "section")
                    chunks.extend(sub_chunks)
                else:
                    # Chunk is appropriate size
                    chunk = ChunkResult(
                        text=chunk_text,
                        entities=[],
                        chunk_type=item.get("type", "section"),
                        article_number=item.get("article_number"),
                        section_title=item.get("title")
                    )
                    chunks.append(chunk)
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                # Continue with next chunk
        
        return chunks
    
    def _chunk_by_paragraphs(self, text: str, max_tokens: int) -> List[ChunkResult]:
        """Chunk by paragraphs with token limit."""
        chunks = []
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        current_tokens = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            paragraph_tokens = len(paragraph.split()) * 2  # Rough estimate
            
            if current_tokens + paragraph_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunks.append(ChunkResult(
                    text=current_chunk.strip(),
                    entities=[],
                    chunk_type="paragraph"
                ))
                current_chunk = paragraph
                current_tokens = paragraph_tokens
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
                current_tokens += paragraph_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append(ChunkResult(
                text=current_chunk.strip(),
                entities=[],
                chunk_type="paragraph"
            ))
        
        return chunks
    
    def _fallback_chunking(self, text: str, max_tokens: int) -> List[ChunkResult]:
        """Fallback chunking method."""
        chunks = []
        
        # Simple sentence-based chunking
        sentences = re.split(r'[.!?。！？]\s*', text)
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_tokens = len(sentence.split()) * 2
            
            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                chunks.append(ChunkResult(
                    text=current_chunk.strip(),
                    entities=[],
                    chunk_type="sentence"
                ))
                current_chunk = sentence
                current_tokens = sentence_tokens
            else:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
                current_tokens += sentence_tokens
        
        if current_chunk:
            chunks.append(ChunkResult(
                text=current_chunk.strip(),
                entities=[],
                chunk_type="sentence"
            ))
        
        return chunks


def llm_chunk_text(text: str, max_tokens: int = 400) -> List[Dict[str, any]]:
    """Main function for LLM-based text chunking."""
    chunker = LLMChunker()
    chunks = chunker.chunk_text(text, max_tokens)
    
    # Convert to dict format
    result = []
    for chunk in chunks:
        # Skip empty chunks
        if not chunk.text or len(chunk.text.strip()) < 10:
            continue
            
        # Ensure chunk ends with proper punctuation if possible
        chunk_text = chunk.text.strip()
        if chunk_text and chunk_text[-1] not in '.!?":\')}]' and len(chunk_text) > 50:
            # Try to find a better ending point
            for punct in ['. ', '! ', '? ', '."', '!"', '?"']:
                last_punct = chunk_text.rfind(punct)
                if last_punct > len(chunk_text) * 0.5:  # Only truncate if we're keeping at least half
                    chunk_text = chunk_text[:last_punct+1].strip()
                    break
        
        # Ensure chunk starts with a capital letter or number if possible
        if chunk_text and chunk_text[0].islower() and len(chunk_text) > 1:
            # This might be a partial sentence, but we'll keep it for now
            # Just log a warning
            logging.warning(f"Chunk starts with lowercase: '{chunk_text[:50]}...'")
        
        result.append({
            "body": chunk_text,
            "entities": chunk.entities,
            "chunk_type": chunk.chunk_type,
            "article_number": chunk.article_number,
            "section_title": chunk.section_title,
            "token_count": chunk.token_count,
            "char_count": len(chunk_text),
            "relationships": chunk.relationships # Added relationships to the result
        })
    
    return result


# Example usage and testing
if __name__ == "__main__":
    # Test with sample Korean legal text
    sample_text = """
    제1조 (목적) 이 법은 전자금융거래의 안전성과 신뢰성을 확보하고 이용자를 보호하기 위하여 필요한 사항을 규정함을 목적으로 한다.
    
    제2조 (정의) 이 법에서 사용하는 용어의 뜻은 다음과 같다.
    1. "전자금융거래"란 금융기관이 전자적 장치를 통하여 금융상품 및 서비스를 제공하고, 이용자가 금융기관의 종사자와 직접 대면하거나 의사소통을 하지 아니하고 자동화된 방식으로 이를 이용하는 거래를 말한다.
    2. "전자적 장치"란 전자금융업무를 처리하기 위하여 이용되는 전자적 방법으로서 대통령령으로 정하는 것을 말한다.
    3. "금융기관"이란 다음 각 호의 어느 하나에 해당하는 기관을 말한다.
    가. 은행법에 따른 은행
    나. 자본시장과 금융투자업에 관한 법률에 따른 투자매매업자, 투자중개업자, 집합투자업자, 신탁업자, 증권금융회사, 종합금융회사 및 명의개서대행회사
    """
    
    print("🧪 Testing LLM-based chunking...")
    chunks = llm_chunk_text(sample_text, max_tokens=200)
    
    for i, chunk in enumerate(chunks):
        print(f"\n📄 Chunk {i+1}:")
        print(f"   Type: {chunk['chunk_type']}")
        print(f"   Article: {chunk.get('article_number', 'N/A')}")
        print(f"   Tokens: {chunk['token_count']}")
        print(f"   Entities: {chunk['entities']}")
        print(f"   Text: {chunk['body'][:100]}...")
