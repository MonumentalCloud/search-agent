#!/usr/bin/env python3
"""
Test script for improved chunking system

This script demonstrates the difference between the old and new chunking approaches.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ingestion.pipeline import _simple_chunk, _improved_chunk_document
from ingestion.improved_chunking import improved_chunk_text, ChunkConfig

def test_chunking_comparison():
    """Compare old vs new chunking approaches."""
    
    # Sample Korean legal text
    sample_text = """
    제1조 (목적) 이 법은 전자금융거래의 안전성과 신뢰성을 확보하고 이용자를 보호하기 위하여 필요한 사항을 규정함을 목적으로 한다.
    
    제2조 (정의) 이 법에서 사용하는 용어의 뜻은 다음과 같다.
    1. "전자금융거래"란 금융기관이 전자적 장치를 통하여 금융상품 및 서비스를 제공하고, 이용자가 금융기관의 종사자와 직접 대면하거나 의사소통을 하지 아니하고 자동화된 방식으로 이를 이용하는 거래를 말한다.
    2. "전자적 장치"란 전자금융업무를 처리하기 위하여 이용되는 전자적 방법으로서 대통령령으로 정하는 것을 말한다.
    3. "금융기관"이란 다음 각 호의 어느 하나에 해당하는 기관을 말한다.
    가. 은행법에 따른 은행
    나. 자본시장과 금융투자업에 관한 법률에 따른 투자매매업자, 투자중개업자, 집합투자업자, 신탁업자, 증권금융회사, 종합금융회사 및 명의개서대행회사
    다. 보험업법에 따른 보험회사
    라. 상호저축은행법에 따른 상호저축은행
    마. 신용협동조합법에 따른 신용협동조합
    바. 새마을금고법에 따른 새마을금고
    사. 산림조합법에 따른 산림조합
    아. 농협법에 따른 농협중앙회 및 지역농협
    자. 수협법에 따른 수협중앙회 및 지역수협
    차. 기타 대통령령으로 정하는 금융기관
    
    제3조 (적용범위) 이 법은 전자금융거래에 대하여 적용한다. 다만, 다음 각 호의 어느 하나에 해당하는 경우에는 그러하지 아니하다.
    1. 전자금융거래의 당사자 간에 별도의 약정이 있는 경우
    2. 전자금융거래의 특성상 이 법의 적용이 부적절하다고 대통령령으로 정하는 경우
    """
    
    print("=" * 80)
    print("CHUNKING COMPARISON TEST")
    print("=" * 80)
    
    # Test old chunking
    print("\n🔴 OLD CHUNKING (Character-based):")
    print("-" * 50)
    old_chunks = _simple_chunk(sample_text, max_chars=200, overlap=50)
    for i, chunk in enumerate(old_chunks):
        print(f"Chunk {i+1} ({len(chunk)} chars):")
        print(f"  {chunk[:100]}...")
        print()
    
    # Test new chunking
    print("\n🟢 NEW CHUNKING (Token-based, Semantic-aware):")
    print("-" * 50)
    
    doc_metadata = {
        "doc_id": "test_doc",
        "section": "test_section",
        "lang": "ko"
    }
    
    new_chunks = _improved_chunk_document(sample_text, doc_metadata)
    for i, chunk_data in enumerate(new_chunks):
        print(f"Chunk {i+1}:")
        print(f"  Tokens: {chunk_data.get('token_count', 'N/A')}")
        print(f"  Characters: {chunk_data.get('char_count', 'N/A')}")
        print(f"  Entities: {chunk_data.get('entities', [])}")
        print(f"  Text: {chunk_data['body'][:100]}...")
        print()
    
    # Test direct improved chunking
    print("\n🔵 DIRECT IMPROVED CHUNKING:")
    print("-" * 50)
    
    config = ChunkConfig(
        max_tokens=100,
        min_tokens=20,
        overlap_tokens=20,
        respect_sentences=True,
        respect_paragraphs=True
    )
    
    direct_chunks = improved_chunk_text(sample_text, config)
    for i, chunk_data in enumerate(direct_chunks):
        print(f"Chunk {i+1}:")
        print(f"  Tokens: {chunk_data.get('token_count', 'N/A')}")
        print(f"  Entities: {chunk_data.get('entities', [])}")
        print(f"  Text: {chunk_data['body'][:100]}...")
        print()

if __name__ == "__main__":
    test_chunking_comparison()
