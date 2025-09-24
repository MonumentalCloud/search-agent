import logging
from typing import List, Dict, Any, Optional
import asyncio

from agent.types import CandidateChunk
from adapters.chroma_adapter import ChromaClient
from memory.retrieval_cache import retrieval_cache
from configs.load import load_yaml_config
import os

# Import our new soft boosting system
from soft_boost_filtering import SoftBoostFilter

logger = logging.getLogger(__name__)

# Load config
_config = load_yaml_config(os.path.join(os.path.dirname(__file__), "..", "..", "configs", "default.yaml"))

def run_branches(query: str, branches: List[Dict[str, Any]]) -> List[CandidateChunk]:
    """Run parallel search branches with different facet filters."""
    all_results = []
    
    # Process each branch
    for branch in branches:
        branch_facets = branch.get("facets", {})
        branch_name = branch.get("name", "Unnamed Branch")
        logger.info(f"Processing branch '{branch_name}' with facets: {branch_facets}")
        
        # Check cache first
        cached_results = retrieval_cache.get_cached_results(query, branch_facets)
        if cached_results is not None:
            logger.info(f"Using cached results for branch '{branch_name}' ({len(cached_results)} results)")
            
            # Add branch info to results
            for result in cached_results:
                result["branch_info"] = {
                    "name": branch_name,
                    "facets": branch_facets
                }
            
            all_results.extend(cached_results)
            continue
        
        # If not in cache, perform the search
        with ChromaClient() as client:
            logger.debug(f"Chroma connection status: {client._connected}")
            if not client._connected:
                logger.warning("Chroma not connected, skipping branch")
                continue
            
            try:
                # Get the stage3 limit from config
                stage3_limit = client.stage3_limit
                
                # Determine limit for this branch
                branch_limit = max(10, stage3_limit // max(1, len(branches)))
                
                # Get collection
                collection = client._client.get_collection(client.chunk_collection)
                
                # Step 1: Get large pool of chunks with semantic search (no hard filters)
                logger.info(f"Getting semantic search results for query: '{query}'")
                
                # Generate query embedding
                from configs.load import get_default_embeddings
                embeddings_model = get_default_embeddings()
                query_vector = embeddings_model.embed_query(query)
                
                # Get large pool of results (no hard filtering)
                # Use configurable large pool size
                large_pool_multiplier = getattr(client, 'large_pool_multiplier', 3)
                max_large_pool_size = getattr(client, 'max_large_pool_size', 100)
                large_pool_size = min(max_large_pool_size, branch_limit * large_pool_multiplier)
                
                semantic_results = collection.query(
                    query_embeddings=[query_vector],
                    n_results=large_pool_size,
                    include=['metadatas', 'documents']
                )
                
                if not semantic_results or 'ids' not in semantic_results or not semantic_results['ids']:
                    logger.warning(f"No semantic results found for branch '{branch_name}'")
                    continue
                
                # Convert to our chunk format
                chunks = []
                for i, chunk_id in enumerate(semantic_results['ids'][0]):
                    metadata = semantic_results['metadatas'][0][i] if 'metadatas' in semantic_results else {}
                    document = semantic_results['documents'][0][i] if 'documents' in semantic_results else ''
                    
                    # Handle None metadata gracefully
                    safe_metadata = metadata or {}
                    
                    chunks.append({
                        'chunk_id': chunk_id,
                        'doc_id': safe_metadata.get('doc_id', ''),
                        'section': safe_metadata.get('section', ''),
                        'body': document,
                        'entities': safe_metadata.get('entities', []),
                        'valid_from': safe_metadata.get('valid_from', ''),
                        'valid_to': safe_metadata.get('valid_to', ''),
                        'metadata': safe_metadata,
                        'document': document
                    })
                
                logger.info(f"Retrieved {len(chunks)} chunks for soft boosting")
                
                # Step 2: Apply soft boosting based on metadata relevance
                soft_filter = SoftBoostFilter()
                boost_info = soft_filter.apply_soft_boosting(chunks, query)
                boosted_chunks = boost_info['boosted_chunks']
                
                # Step 3: Take top results based on boost scores
                top_results = boosted_chunks[:branch_limit]
                
                # Convert back to expected format
                branch_results = []
                for chunk, boost_score in top_results:
                    result = {
                        'chunk_id': chunk['chunk_id'],
                        'doc_id': chunk['doc_id'],
                        'section': chunk['section'],
                        'body': chunk['body'],
                        'entities': chunk['entities'],
                        'valid_from': chunk['valid_from'],
                        'valid_to': chunk['valid_to'],
                        'metadata': chunk['metadata'],
                        'boost_score': boost_score  # Add boost score for debugging
                    }
                    branch_results.append(result)
                
                # Add branch info to results
                for result in branch_results:
                    result["branch_info"] = {
                        "name": branch_name,
                        "facets": branch_facets
                    }
                
                # Cache the results
                retrieval_cache.cache_results(query, branch_results, branch_facets)
                
                all_results.extend(branch_results)
                logger.info(f"Branch returned {len(branch_results)} results (top boost scores: {[f'{x[1]:.2f}' for x in boosted_chunks[:3]]})")
                
            except Exception as e:
                logger.error(f"Branch search failed: {e}", exc_info=True)
    
    # Deduplicate by chunk_id
    deduplicated = {}
    for result in all_results:
        chunk_id = result.get("chunk_id")
        if chunk_id and chunk_id not in deduplicated:
            deduplicated[chunk_id] = result
    
    final_results = list(deduplicated.values())
    logger.info(f"Narrowed search with soft boosting returned {len(final_results)} total results after deduplication")
    
    return final_results