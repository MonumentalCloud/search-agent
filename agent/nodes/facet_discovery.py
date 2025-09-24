import logging
from collections import Counter
from typing import Dict, List

from agent.types import CandidateChunk
from adapters.chroma_adapter import ChromaClient

logger = logging.getLogger(__name__)


def discover_facets(candidates: List[CandidateChunk]) -> Dict[str, Dict[str, int]]:
    """Discover facet statistics from candidates and corpus."""
    # Dynamically fetch facet names from Chroma
    with ChromaClient() as client:
        if client._connected:
            facets = client.get_chunk_facets()
            if not facets:
                logger.warning("No facets discovered from schema; falling back to default facets.")
                facets = ["doc_type", "section", "jurisdiction", "lang"]
        else:
            logger.warning("Chroma not connected, falling back to default facets.")
            facets = ["doc_type", "section", "jurisdiction", "lang"]

    # First, get histograms from candidates
    hist: Dict[str, Counter] = {facet: Counter() for facet in facets}

    for c in candidates:
        md = c.get("metadata", {})
        for k in facets:
            v = md.get(k)
            if isinstance(v, str) and v:
                hist[k][v] += 1
            elif isinstance(v, list):
                # Handle list values by converting to string
                for item in v:
                    if isinstance(item, str) and item:
                        hist[k][item] += 1
        # Also handle entities field which is a list (if present in facets)
        if "entities" in facets:
            entities = c.get("entities", [])
            if isinstance(entities, list):
                for entity in entities:
                    if isinstance(entity, str) and entity:
                        hist["entities"] = hist.get("entities", Counter())
                        hist["entities"][entity] += 1

    # Also get corpus-wide statistics from Chroma
    with ChromaClient() as client:
        if client._connected:
            try:
                for facet in facets:
                    corpus_counts = client.aggregate_group_by(facet)
                    for value, count in corpus_counts.items():
                        hist[facet][value] += count
            except Exception as e:
                logger.warning(f"Could not get corpus statistics: {e}")

    # Convert to plain dicts
    result = {k: dict(v) for k, v in hist.items()}
    logger.debug(f"Discovered facets: {result}")

    return result