from typing import List, Optional
from pydantic import BaseModel


class Document(BaseModel):
    doc_id: str
    title: str
    entities: List[str] = []
    topics: List[str] = []
    jurisdiction: Optional[str] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    doc_type: Optional[str] = None
    lang: Optional[str] = None


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    section: Optional[str] = None
    body: str
    entities: List[str] = []
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

