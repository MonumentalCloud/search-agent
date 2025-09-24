import logging
from datetime import datetime
from typing import List, Dict, Any

from configs.load import get_default_embeddings
from adapters.weaviate_adapter import WeaviateClient

logger = logging.getLogger(__name__)


def _get_embedding_model():
    """Get the embedding model for facet-value vectors."""
    try:
        return get_default_embeddings()
    except Exception as e:
        logger.warning(f"Could not load embedding model: {e}")
        return None


def _build_facet_value_description(facet: str, value: str, sample_sentences: List[str] = None) -> str:
    """Build a description for a facet-value pair."""
    descriptions = {
        "doc_type": "This is a document type",
        "section": "This is a section label",
        "jurisdiction": "This is a jurisdiction",
        "lang": "This is a language code",
    }
    
    base_desc = descriptions.get(facet, f"This is a {facet}")
    desc = f"{base_desc} meaning {value}"
    
    if sample_sentences:
        desc += f". Examples: {' '.join(sample_sentences[:3])}"
    
    return desc


def _get_sample_sentences_for_facet_value(client: WeaviateClient, facet: str, value: str, limit: int = 5) -> List[str]:
    """Get sample sentences from chunks that have this facet value."""
    try:
        # Search for chunks with this facet value
        where_filter = {facet: value}
        results = client.hybrid_search(
            query=value,  # Use the value as query
            alpha=0.5,
            limit=limit,
            where=where_filter
        )
        
        sentences = []
        for result in results:
            body = result.get("body", "")
            if body:
                # Take first sentence or first 100 chars
                first_sentence = body.split('.')[0][:100]
                if first_sentence:
                    sentences.append(first_sentence)
        
        return sentences
        
    except Exception as e:
        logger.warning(f"Could not get sample sentences for {facet}={value}: {e}")
        return []


def rebuild_all_facet_value_vectors(trace_id: str | None = None) -> int:
    """Rebuild all facet-value vectors from the corpus."""
    with WeaviateClient() as client:
        if not client._connected:
            logger.warning("Not connected to Weaviate, cannot rebuild facet vectors")
            return 0
        
        model = _get_embedding_model()
        if model is None:
            logger.warning("No embedding model available, cannot rebuild facet vectors")
            return 0
        
        try:
            # Get all unique values for each facet
            facets = ["doc_type", "section", "jurisdiction", "lang"]
            total_updated = 0
            
            for facet in facets:
                logger.info(f"Rebuilding vectors for facet: {facet}")
                
                # Get unique values for this facet
                values = client.aggregate_group_by(facet)
                
                for value, count in values.items():
                    if count > 0:  # Only process values that exist
                        logger.debug(f"Processing {facet}={value} (count: {count})")
                        
                        # Get sample sentences from chunks with this value
                        sample_sentences = _get_sample_sentences_for_facet_value(client, facet, value)
                        
                        # Build description
                        description = _build_facet_value_description(facet, value, sample_sentences)
                        
                        # Generate aliases (spacing variants for Korean)
                        aliases = []
                        if facet in ["section", "doc_type"] and " " in value:
                            aliases.append(value.replace(" ", ""))
                        
                        # Create embedding
                        vector = model.embed_query(description)
                        
                        # Upsert to Weaviate
                        success = client.upsert_facet_value_vector(facet, value, vector, aliases)
                        if success:
                            total_updated += 1
                            logger.debug(f"Updated vector for {facet}={value}")
                        else:
                            logger.warning(f"Failed to update vector for {facet}={value}")
            
            logger.info(f"Rebuilt {total_updated} facet-value vectors")
            return total_updated
            
        except Exception as e:
            logger.error(f"Failed to rebuild facet vectors: {e}")
            return 0


def get_facet_weights_for_query(query: str, facets: List[str] = None) -> Dict[str, Dict[str, float]]:
    """Get facet weights for a query using facet-value vectors."""
    with WeaviateClient() as client:
        if not client._connected:
            return {}
        
        model = _get_embedding_model()
        if model is None:
            return {}
        
        try:
            # Embed the query
            query_vector = model.embed_query(query)
            
            if facets is None:
                facets = ["doc_type", "section", "jurisdiction", "lang"]
            
            facet_weights = {}
            
            for facet in facets:
                # Get all facet-value vectors for this facet
                vectors = client.get_facet_vectors(facet)
                
                if not vectors:
                    continue
                
                # Compute similarities
                similarities = []
                for vector_data in vectors:
                    value = vector_data["value"]
                    vector = vector_data["vector"]
                    aliases = vector_data.get("aliases", [])
                    
                    # Compute cosine similarity
                    import numpy as np
                    query_np = np.array(query_vector)
                    vector_np = np.array(vector)
                    
                    # Normalize vectors
                    query_norm = query_np / (np.linalg.norm(query_np) + 1e-8)
                    vector_norm = vector_np / (np.linalg.norm(vector_np) + 1e-8)
                    
                    similarity = float(np.dot(query_norm, vector_norm))
                    similarities.append((value, similarity))
                
                # Sort by similarity and take top values
                similarities.sort(key=lambda x: x[1], reverse=True)
                top_values = similarities[:2]  # Top 2 per facet
                
                facet_weights[facet] = {value: sim for value, sim in top_values if sim > 0.1}
            
            return facet_weights
            
        except Exception as e:
            logger.error(f"Failed to get facet weights: {e}")
            return {}


# Create an alias for rebuild_all_facet_value_vectors for backward compatibility
def rebuild_all_facet_vectors(trace_id: str | None = None) -> int:
    """Alias for rebuild_all_facet_value_vectors for backward compatibility."""
    return rebuild_all_facet_value_vectors(trace_id)