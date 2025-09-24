import asyncio
import sys
from pathlib import Path
import os
import json
import logging

# Add project root and utils directory to Python path
project_root = Path(__file__).parent # Corrected: only one .parent needed
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "utils"))

from configs.load import setup_root_logger, load_yaml_config
from adapters.weaviate_adapter import WeaviateClient

# Setup logging
setup_root_logger(logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_weaviate():
    logger.info("🚀 Starting Weaviate debug script...")
    
    with WeaviateClient() as client:
        if not client._connected:
            logger.error("❌ Weaviate is NOT connected. Please ensure Weaviate Docker is running.")
            return
        logger.info("✅ Successfully connected to Weaviate.")

        # Verify schema
        logger.info("🔍 Verifying Weaviate schema...")
        if not client.ensure_schema():
            logger.error("❌ Failed to ensure Weaviate schema. Collections might be missing or malformed.")
            return
        logger.info("✅ Weaviate schema verified (Document, Chunk, FacetValueVector, ChunkStats collections exist or were created).")

        # Verify document count
        logger.info(" Checking Document count...")
        doc_collection = client._client.collections.get(client.document_class)
        doc_count = doc_collection.aggregate.over_all(total_count=True) # Removed await
        logger.info(f"Total Documents: {doc_count.total_count}")

        # Verify chunk count
        logger.info(" Checking Chunk count...")
        chunk_collection = client._client.collections.get(client.chunk_class)
        chunk_count = chunk_collection.aggregate.over_all(total_count=True) # Removed await
        logger.info(f"Total Chunks: {chunk_count.total_count}")

        # Verify FacetValueVector count
        logger.info(" Checking FacetValueVector count...")
        facet_vector_collection = client._client.collections.get("FacetValueVector")
        facet_vector_count = facet_vector_collection.aggregate.over_all(total_count=True) # Removed await
        logger.info(f"Total FacetValueVectors: {facet_vector_count.total_count}")

        if chunk_count.total_count == 0:
            logger.warning("⚠️  No chunks found in Weaviate. Ingestion might have failed.")
            logger.info("💡 Suggestion: Run `python reset_db.py --verbose` to re-ingest PDFs.")
        else:
            logger.info("✅ Chunks found. Proceeding to test search.")
            
            # Test hybrid_search directly
            test_query = "전자금융거래법 시행령에서 규정하는 내용은 무엇인가요?"
            logger.info(f"Testing hybrid_search with query: \"{test_query}\"")
            
            try:
                # Load alpha from config
                _config = load_yaml_config(project_root / "configs" / "default.yaml")
                alpha = _config["search_backend"]["weaviate"].get("default_alpha", 0.5)

                # Call hybrid_search (now async)
                search_results = await client.hybrid_search(query=test_query, alpha=alpha, limit=5)
                
                if search_results:
                    logger.info(f"✅ hybrid_search returned {len(search_results)} results.")
                    for i, res in enumerate(search_results[:3]): # Print first 3 results
                        logger.info(f"  Result {i+1}: Chunk ID={res.get('chunk_id')}, Score={res.get('score')}, Body={res.get('body', '')[:50]}...")
                else:
                    logger.warning("⚠️  hybrid_search returned no results.")

            except ConnectionError as ce:
                logger.error(f"❌ ConnectionError during hybrid_search test: {ce}")
            except Exception as e:
                logger.error(f"❌ Error during hybrid_search test: {e}", exc_info=True)
        
        # Test get_facet_vectors directly
        if facet_vector_count.total_count > 0:
            logger.info("Testing get_facet_vectors...")
            test_facet = "doc_type"
            try:
                facet_vectors = await client.get_facet_vectors(test_facet)
                if facet_vectors:
                    logger.info(f"✅ get_facet_vectors returned {len(facet_vectors)} vectors for facet '{test_facet}'.")
                    for i, vec_data in enumerate(facet_vectors[:2]):
                        logger.info(f"  Facet Vector {i+1}: Value={vec_data.get('value')}, Updated={vec_data.get('updated_at')}")
                else:
                    logger.warning(f"⚠️  get_facet_vectors returned no vectors for facet '{test_facet}'.")
            except ConnectionError as ce:
                logger.error(f"❌ ConnectionError during get_facet_vectors test: {ce}")
            except Exception as e:
                logger.error(f"❌ Error during get_facet_vectors test: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(debug_weaviate())
