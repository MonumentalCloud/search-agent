"""
Improved Chunking System

This module provides better chunking strategies that respect:
- Token boundaries (not character boundaries)
- Sentence boundaries
- Semantic coherence
- Korean text characteristics
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logging.warning("tiktoken not available, falling back to character-based chunking")

try:
    import spacy
    from spacy import displacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning("spacy not available, using simple entity extraction")

logger = logging.getLogger(__name__)


@dataclass
class ChunkConfig:
    """Configuration for chunking parameters."""
    max_tokens: int = 400
    min_tokens: int = 50
    overlap_tokens: int = 50
    model_name: str = "gpt-3.5-turbo"  # For tiktoken
    respect_sentences: bool = True
    respect_paragraphs: bool = True
    semantic_chunking: bool = True


class Tokenizer:
    """Token counting utility."""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.model_name = model_name
        self.encoding = None
        
        if TIKTOKEN_AVAILABLE:
            try:
                self.encoding = tiktoken.encoding_for_model(model_name)
            except KeyError:
                # Fallback to cl100k_base encoding
                self.encoding = tiktoken.get_encoding("cl100k_base")
                logger.warning(f"Model {model_name} not found, using cl100k_base encoding")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Fallback: rough estimate (1 token ≈ 4 characters for Korean)
            return len(text) // 4
    
    def encode(self, text: str) -> List[int]:
        """Encode text to tokens."""
        if self.encoding:
            return self.encoding.encode(text)
        else:
            # Fallback: return character indices
            return list(range(len(text)))


class KoreanEntityExtractor:
    """Korean-specific entity extraction."""
    
    def __init__(self):
        self.nlp = None
        if SPACY_AVAILABLE:
            try:
                # Try to load Korean model
                self.nlp = spacy.load("ko_core_news_sm")
            except OSError:
                logger.warning("Korean spaCy model not found, using simple extraction")
                self.nlp = None
    
    def extract_entities(self, text: str) -> List[str]:
        """Extract entities from Korean text."""
        entities = []
        
        if self.nlp:
            # Use spaCy for proper NER
            doc = self.nlp(text)
            for ent in doc.ents:
                entities.append(ent.text)
        else:
            # Simple pattern-based extraction for Korean legal documents
            entities.extend(self._extract_korean_legal_entities(text))
        
        return list(set(entities))  # Remove duplicates
    
    def _extract_korean_legal_entities(self, text: str) -> List[str]:
        """Extract Korean legal entities using patterns."""
        entities = []
        
        # Korean legal patterns
        patterns = [
            r'[가-힣]+법',  # 법 (law)
            r'[가-힣]+령',  # 령 (decree)
            r'[가-힣]+규정',  # 규정 (regulation)
            r'[가-힣]+감독원',  # 감독원 (supervisory authority)
            r'[가-힣]+위원회',  # 위원회 (committee)
            r'[가-힣]+은행',  # 은행 (bank)
            r'[가-힣]+금융',  # 금융 (finance)
            r'제\d+조',  # Article X
            r'제\d+장',  # Chapter X
            r'제\d+절',  # Section X
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            entities.extend(matches)
        
        return entities


class SemanticChunker:
    """Semantic-aware chunking that respects meaning boundaries."""
    
    def __init__(self, config: ChunkConfig = None):
        self.config = config or ChunkConfig()
        self.tokenizer = Tokenizer(self.config.model_name)
        self.entity_extractor = KoreanEntityExtractor()
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict[str, any]]:
        """Chunk text into semantically coherent pieces."""
        if not text.strip():
            return []
        
        # Step 1: Split into paragraphs
        paragraphs = self._split_paragraphs(text)
        
        # Step 2: Process each paragraph
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for paragraph in paragraphs:
            paragraph_tokens = self.tokenizer.count_tokens(paragraph)
            
            # If paragraph is too large, split it further
            if paragraph_tokens > self.config.max_tokens:
                sub_chunks = self._split_large_paragraph(paragraph)
                for sub_chunk in sub_chunks:
                    chunks.extend(self._process_chunk(sub_chunk, metadata))
            else:
                # Check if adding this paragraph would exceed max tokens
                if current_tokens + paragraph_tokens > self.config.max_tokens and current_chunk:
                    # Save current chunk
                    chunks.extend(self._process_chunk(current_chunk, metadata))
                    current_chunk = paragraph
                    current_tokens = paragraph_tokens
                else:
                    # Add to current chunk
                    if current_chunk:
                        current_chunk += "\n\n" + paragraph
                    else:
                        current_chunk = paragraph
                    current_tokens += paragraph_tokens
        
        # Process final chunk
        if current_chunk:
            chunks.extend(self._process_chunk(current_chunk, metadata))
        
        # Add overlap between chunks
        if self.config.overlap_tokens > 0:
            chunks = self._add_overlap(chunks)
        
        return chunks
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split on double newlines, but preserve single newlines within paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_large_paragraph(self, paragraph: str) -> List[str]:
        """Split large paragraphs into smaller chunks."""
        if self.config.respect_sentences:
            return self._split_by_sentences(paragraph)
        else:
            return self._split_by_tokens(paragraph)
    
    def _split_by_sentences(self, text: str) -> List[str]:
        """Split text by sentence boundaries."""
        # Korean sentence patterns
        sentence_endings = r'[.!?。！？]\s*'
        sentences = re.split(sentence_endings, text)
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_tokens = self.tokenizer.count_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.config.max_tokens and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
                current_tokens = sentence_tokens
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_tokens += sentence_tokens
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _split_by_tokens(self, text: str) -> List[str]:
        """Split text by token count (fallback method)."""
        tokens = self.tokenizer.encode(text)
        chunks = []
        
        for i in range(0, len(tokens), self.config.max_tokens):
            chunk_tokens = tokens[i:i + self.config.max_tokens]
            if self.tokenizer.encoding:
                chunk_text = self.tokenizer.encoding.decode(chunk_tokens)
            else:
                # Fallback: use character slicing
                start_char = i * 4  # Rough estimate
                end_char = min(len(text), (i + self.config.max_tokens) * 4)
                chunk_text = text[start_char:end_char]
            
            chunks.append(chunk_text)
        
        return chunks
    
    def _process_chunk(self, chunk_text: str, metadata: Dict = None) -> List[Dict[str, any]]:
        """Process a single chunk and extract metadata."""
        if not chunk_text.strip():
            return []
        
        # Extract entities
        entities = self.entity_extractor.extract_entities(chunk_text)
        
        # Create chunk object
        chunk = {
            "body": chunk_text,
            "entities": entities,
            "token_count": self.tokenizer.count_tokens(chunk_text),
            "char_count": len(chunk_text),
        }
        
        # Add metadata if provided
        if metadata:
            chunk.update(metadata)
        
        return [chunk]
    
    def _add_overlap(self, chunks: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """Add overlap between chunks."""
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = []
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped_chunks.append(chunk)
                continue
            
            # Get previous chunk
            prev_chunk = chunks[i - 1]
            prev_text = prev_chunk["body"]
            
            # Extract overlap from previous chunk
            prev_tokens = self.tokenizer.encode(prev_text)
            if len(prev_tokens) > self.config.overlap_tokens:
                overlap_tokens = prev_tokens[-self.config.overlap_tokens:]
                if self.tokenizer.encoding:
                    overlap_text = self.tokenizer.encoding.decode(overlap_tokens)
                else:
                    # Fallback
                    overlap_text = prev_text[-self.config.overlap_tokens * 4:]
                
                # Add overlap to current chunk
                chunk["body"] = overlap_text + "\n\n" + chunk["body"]
                chunk["token_count"] = self.tokenizer.count_tokens(chunk["body"])
                chunk["char_count"] = len(chunk["body"])
            
            overlapped_chunks.append(chunk)
        
        return overlapped_chunks


def improved_chunk_text(text: str, config: ChunkConfig = None, metadata: Dict = None) -> List[Dict[str, any]]:
    """Main function for improved text chunking."""
    chunker = SemanticChunker(config)
    return chunker.chunk_text(text, metadata)


# Example usage and testing
if __name__ == "__main__":
    # Test with sample Korean legal text
    sample_text = """
    제1조 (목적) 이 법은 전자금융거래의 안전성과 신뢰성을 확보하고 이용자를 보호하기 위하여 필요한 사항을 규정함을 목적으로 한다.
    
    제2조 (정의) 이 법에서 사용하는 용어의 뜻은 다음과 같다.
    1. "전자금융거래"란 금융기관이 전자적 장치를 통하여 금융상품 및 서비스를 제공하고, 이용자가 금융기관의 종사자와 직접 대면하거나 의사소통을 하지 아니하고 자동화된 방식으로 이를 이용하는 거래를 말한다.
    2. "전자적 장치"란 전자금융업무를 처리하기 위하여 이용되는 전자적 방법으로서 대통령령으로 정하는 것을 말한다.
    """
    
    config = ChunkConfig(max_tokens=100, overlap_tokens=20)
    chunks = improved_chunk_text(sample_text, config)
    
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}:")
        print(f"  Tokens: {chunk['token_count']}")
        print(f"  Entities: {chunk['entities']}")
        print(f"  Text: {chunk['body'][:100]}...")
        print()
