from typing import Dict, List, Tuple, Optional

import numpy as np
from agent.types import CandidateChunk, RerankedChunk
from adapters.rankers import CrossEncoderReranker, mmr_select
from configs.load import get_default_embeddings
from memory.stores import get_best_query_cluster_similarity


def rerank_and_diversify(query: str, candidates: List[CandidateChunk], plan: Dict) -> tuple[List[RerankedChunk], int]:
    if not candidates:
        return [], 0
    
    # Get query embedding for memory similarity calculation
    query_embedding = None
    try:
        embeddings_model = get_default_embeddings()
        query_embedding = embeddings_model.embed_query(query)
        print(f"[RERANK] Generated query embedding for memory boosting")
    except Exception as e:
        print(f"[RERANK] Failed to generate query embedding: {e}")
        query_embedding = None
    
    # Cross-encoder reranking
    reranker = CrossEncoderReranker()
    pairs = [(query, c.get("body", "")) for c in candidates]
    scores = reranker.score(pairs)
    
    # Memory-based boosting parameters
    memory_weight = 0.3  # How much to weight memory similarity (0-1)
    
    enriched: List[RerankedChunk] = []
    boosted_count = 0
    for c, s in zip(candidates, scores):
        chunk_id = c.get("chunk_id", "")
        
        # Base reranker score
        rerank_score = float(s)
        
        # Memory boost based on query centroid similarity
        memory_score = 0.0
        if query_embedding and chunk_id:
            memory_score = get_best_query_cluster_similarity(chunk_id, query_embedding)
            
            # Apply memory boost
            if memory_score > 0:
                # Combine scores: (1-w)*rerank_score + w*memory_score
                combined_score = (1.0 - memory_weight) * rerank_score + memory_weight * memory_score
                print(f"[RERANK] Boosted chunk {chunk_id}: {rerank_score:.3f} → {combined_score:.3f} (memory_sim={memory_score:.3f})")
                rerank_score = combined_score
                boosted_count += 1
        
        enriched.append({
            "chunk_id": chunk_id,
            "doc_id": c.get("doc_id", ""),
            "section": c.get("section"),
            "body": c.get("body", ""),
            "entities": c.get("entities", []),
            "score": float(c.get("score", 0.0)),
            "rerank_score": rerank_score,
            "memory_score": memory_score,
        })
    
    # Sort by rerank score
    enriched.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
    
    # Diversity via MMR on simple metadata features
    items = [(
        e["rerank_score"],
        {
            "entities": tuple(sorted(e.get("entities", [])[:5])) if e.get("entities") else 
                      tuple(sorted(e.get("body", "").split()[:5])),
            "section": e.get("section"),
        },
        e,
    ) for e in enriched]
    
    selected = mmr_select(items, lambda_score=0.4, top_k=min(40, len(items)))
    return selected, boosted_count

