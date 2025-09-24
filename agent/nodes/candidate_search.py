import logging
from typing import List, Dict, Any, Optional, Set
import asyncio

from agent.types import CandidateChunk
from adapters.weaviate_adapter import WeaviateClient
from adapters.soft_filters import apply_soft_filters
from configs.load import get_default_embeddings, load_yaml_config
import os

logger = logging.getLogger(__name__)

# Load facet configuration once
_config = load_yaml_config(os.path.join(os.path.dirname(__file__), "..", "..", "configs", "default.yaml"))
FACETS_TO_CONSIDER = _config["facets"]["names"]
TOP_K_PER_FACET = _config["facets"]["soft_vector"]["top_per_facet"]

def first_pass_search(query: str, alpha: float) -> List[CandidateChunk]:
    """First-pass hybrid search to get candidate chunks, with soft metadata filtering."""
    with WeaviateClient() as client:
        logger.debug(f"Weaviate connection status: {client._connected}")
        if not client._connected:
            logger.warning("Weaviate not connected, returning empty results")
            return []
        
        try:
            embeddings_model = get_default_embeddings() 
            query_embedding = embeddings_model.embed_query(query)

            # Get semantically similar hard filters for facets
            dynamic_filters = {} # Initialize empty
            # TODO: Restore semantic facet filtering when method is available
            # try:
            #     dynamic_filters = client.get_semantically_similar_facet_filters(
            #         query_embedding=query_embedding,
            #         facets_to_consider=FACETS_TO_CONSIDER,
            #         top_k_per_facet=TOP_K_PER_FACET
            #     )
            # except ConnectionError as ce:
            #     logger.warning(f"Connection error getting dynamic filters: {ce}. Continuing without semantic filters.")
            # except Exception as e:
            #     logger.error(f"Error getting dynamic filters: {e}", exc_info=True)
            logger.info(f"Dynamic filters generated: {dynamic_filters}")
            logger.debug(f"Dynamic filters types: {[(k, type(v).__name__, v) for k, v in dynamic_filters.items()]}")

            all_results_lists = []

            # Helper to create a search operation, handling ConnectionError
            def _run_search_task(search_query: str, search_alpha: float, search_limit: int, search_where: Optional[Dict[str, Any]] = None):
                try:
                    if search_where:
                        # Use soft filters for more flexible matching
                        logger.info(f"Using soft filters with facets: {search_where}")
                        return apply_soft_filters(
                            collection=client._client.collections.get(client.chunk_class),
                            query=search_query,
                            facets=search_where,
                            alpha=search_alpha,
                            limit=search_limit
                        )
                    else:
                        # Use regular hybrid search for queries without filters
                        return client.hybrid_search(
                            query=search_query,
                            alpha=search_alpha,
                            limit=search_limit,
                            where=None
                        )
                except ConnectionError as ce:
                    logger.warning(f"Connection error during hybrid search: {ce}. Returning empty results for this task.")
                    return []
                except Exception as e:
                    logger.error(f"Error during hybrid search: {e}", exc_info=True)
                    return []

            # 1. Base search (no additional filters)
            all_results_lists.append(_run_search_task(
                search_query=query, # Pass as search_query
                search_alpha=alpha, 
                search_limit=client.stage1_limit
            ))

            # 2. Parallel searches with dynamic hard filters
            num_dynamic_filters = len(dynamic_filters)
            # Distribute limit more evenly, ensuring at least 1 for base search
            base_limit_per_task = max(1, client.stage1_limit // (num_dynamic_filters + 1))

            for facet_name, values in dynamic_filters.items():
                if values and isinstance(values, list): # Ensure there are values for the filter and it's a list
                    where_filter = {facet_name: values}
                    all_results_lists.append(_run_search_task(
                        search_query=query, # Pass as search_query
                        search_alpha=alpha, 
                        search_limit=base_limit_per_task,
                        search_where=where_filter
                    ))
                elif values and isinstance(values, str): # Handle single string values
                    where_filter = {facet_name: [values]} # Convert to list for consistency
                    all_results_lists.append(_run_search_task(
                        search_query=query, # Pass as search_query
                        search_alpha=alpha, 
                        search_limit=base_limit_per_task,
                        search_where=where_filter
                    ))

            # Aggregate and deduplicate results
            combined_results: Dict[str, CandidateChunk] = {}
            for results_list in all_results_lists:
                for chunk in results_list:
                    if chunk and chunk.get("chunk_id"):
                        chunk_id = chunk["chunk_id"]
                        # Ensure chunk_id is a string, not a list
                        if isinstance(chunk_id, list):
                            chunk_id = str(chunk_id[0]) if chunk_id else "unknown"
                        elif not isinstance(chunk_id, str):
                            chunk_id = str(chunk_id)
                        combined_results[chunk_id] = chunk
            
            final_results = list(combined_results.values())

            logger.info(f"Candidate search returned {len(final_results)} aggregated candidates")
            logger.debug(f"Final results: {[r.get('chunk_id', 'No ID') for r in final_results]}")
            return final_results
            
        except Exception as e:
            logger.error(f"Candidate search failed: {e}", exc_info=True)
            return []