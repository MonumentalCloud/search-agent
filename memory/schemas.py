from typing import Dict, List, Optional
from pydantic import BaseModel


class QueryCluster(BaseModel):
    """Represents a cluster of similar queries that found a chunk useful."""
    centroid: List[float]
    count: int = 1
    last_updated: Optional[str] = None
    sample_queries: List[str] = []  # Store a few sample queries for debugging/explainability

class ChunkStats(BaseModel):
    chunk_id: str
    useful_count: int = 0
    last_useful_at: Optional[str] = None
    intent_hist: Dict[str, int] = {}
    entity_hist: Dict[str, int] = {}
    query_centroids: List[QueryCluster] = []  # Multiple centroids instead of just one
    query_centroid: List[float] = []  # Keep for backward compatibility
    decayed_utility: float = 0.0


class QueryProfile(BaseModel):
    query_hash: str
    intent: str
    entities: List[str]
    time_hint: Optional[str]
    alpha_used: float
    ts: str


class RetrievalEvent(BaseModel):
    query_hash: str
    chunk_id: str
    doc_id: str
    scores: Dict[str, float]
    final_rank: int
    selected: bool
    ts: str


class Outcome(BaseModel):
    query_hash: str
    validator_yes: bool
    confidence: float
    user_feedback: Optional[str] = None
    latency_ms: int


class FacetValueVector(BaseModel):
    facet: str
    value: str
    vector: List[float]
    aliases: List[str] = []
    updated_at: str

