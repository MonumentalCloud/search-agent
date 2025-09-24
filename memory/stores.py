from typing import Dict, List, Optional

from memory.schemas import ChunkStats, QueryProfile, RetrievalEvent, Outcome, FacetValueVector


# In-memory session store (e.g., could be replaced by Redis)
SESSION: Dict[str, Dict] = {}

# In-memory persistent-like stores (replace with Postgres/Weaviate later)
CHUNK_STATS: Dict[str, ChunkStats] = {}
QUERY_PROFILES: List[QueryProfile] = []
RETRIEVAL_EVENTS: List[RetrievalEvent] = []
OUTCOMES: List[Outcome] = []
FACET_VALUE_VECTORS: Dict[tuple[str, str], FacetValueVector] = {}


def get_chunk_stats(chunk_id: str) -> ChunkStats:
    if chunk_id not in CHUNK_STATS:
        CHUNK_STATS[chunk_id] = ChunkStats(chunk_id=chunk_id)
    return CHUNK_STATS[chunk_id]


def get_best_query_cluster_similarity(chunk_id: str, query_embedding: List[float]) -> float:
    """Get the similarity score between a query and the best matching query cluster for a chunk.
    
    Args:
        chunk_id: The ID of the chunk to check
        query_embedding: The embedding of the current query
        
    Returns:
        float: The highest cosine similarity score (0-1) between the query and any cluster centroid,
               or 0.0 if no clusters exist or chunk_id not found
    """
    if chunk_id not in CHUNK_STATS:
        return 0.0
    
    chunk_stats = CHUNK_STATS[chunk_id]
    
    # If no clusters, return 0
    if not chunk_stats.query_centroids or len(chunk_stats.query_centroids) == 0:
        return 0.0
    
    # Convert query embedding to numpy array
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    
    query_np = np.array(query_embedding).reshape(1, -1)
    
    # Get all centroids as numpy arrays
    centroids = np.array([cluster.centroid for cluster in chunk_stats.query_centroids])
    
    # Calculate cosine similarities
    similarities = cosine_similarity(query_np, centroids)[0]
    
    # Return the highest similarity
    return float(np.max(similarities)) if len(similarities) > 0 else 0.0


def upsert_facet_value_vector(facet: str, value: str, vector: List[float], aliases: Optional[List[str]], updated_at: str) -> None:
    FACET_VALUE_VECTORS[(facet, value)] = FacetValueVector(
        facet=facet, value=value, vector=vector, aliases=aliases or [], updated_at=updated_at
    )


def get_facet_vectors_for_facet(facet: str) -> List[FacetValueVector]:
    return [v for (f, _), v in FACET_VALUE_VECTORS.items() if f == facet]

