from typing import Dict, List, Optional, TypedDict, Literal, Any


Intent = Literal["legal", "howto", "definition", "other"]


class PlannerOutput(TypedDict, total=False):
    intent: Intent
    entities: List[str]
    time_hint: Optional[str]
    alpha: float
    facet_sets: List[Dict[str, str]]


class CandidateChunk(TypedDict, total=False):
    chunk_id: str
    doc_id: str
    section: Optional[str]
    body: str
    score: float
    metadata: Dict[str, Any]


class RerankedChunk(TypedDict, total=False):
    chunk_id: str
    doc_id: str
    section: Optional[str]
    body: str
    score: float
    rerank_score: float


class Answer(TypedDict, total=False):
    text: str
    citations: List[Dict[str, Any]]

