import os
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import json

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings
from configs.load import load_yaml_config, get_default_embeddings

from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
logger = logging.getLogger(__name__)


class ChromaClient:
    def __init__(self) -> None:
        cfg = load_yaml_config(os.path.join(os.path.dirname(__file__), "..", "configs", "default.yaml"))
        chroma_cfg = cfg["search_backend"].get("chroma", {})
        self.persist_directory = chroma_cfg.get("persist_directory", "./chroma_db")
        self.chunk_collection = chroma_cfg.get("collections", {}).get("chunk", "Chunk")
        self.document_collection = chroma_cfg.get("collections", {}).get("document", "Document")
        self.default_alpha = float(chroma_cfg.get("default_alpha", 0.5))
        self.stage1_limit = int(chroma_cfg.get("stage1_limit", 300))
        self.stage3_limit = int(chroma_cfg.get("stage3_limit", 200))
        
        # Soft boosting configuration
        self.large_pool_multiplier = int(chroma_cfg.get("large_pool_multiplier", 3))
        self.max_large_pool_size = int(chroma_cfg.get("max_large_pool_size", 100))
        
        self._client = None
        self._connected = False
        
        # Connect to Chroma

        # Use the default embeddings from the config for consistent dimensions
        from configs.load import get_default_embeddings
        from chromadb.utils import embedding_functions
        
        # Create a custom embedding function that uses the default embeddings
        class ConfigEmbeddingFunction(embedding_functions.EmbeddingFunction):
            def __init__(self):
                self.embedding_model = get_default_embeddings()
            
            def __call__(self, texts):
                # Convert single text to list if needed
                if isinstance(texts, str):
                    texts = [texts]
                
                # Use the default embeddings model to embed the texts
                embeddings = self.embedding_model.embed_documents(texts)
                return embeddings
        
        # Use the custom embedding function
        self.embedding_function = ConfigEmbeddingFunction()
        self.connect()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def connect(self) -> bool:
        """Connect to Chroma."""
        try:
            self._client = chromadb.PersistentClient(path=self.persist_directory)
            self._connected = True
            logger.info(f"Connected to Chroma at {self.persist_directory}")
            
            # Ensure collections exist
            self.ensure_schema()
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Chroma: {e}")
            self._connected = False
            return False
    
    def close(self) -> None:
        """Close the connection to Chroma."""
        self._connected = False
        self._client = None
    
    def ensure_schema(self) -> bool:
        """Ensure that the required collections exist."""
        if not self._connected or self._client is None:
            logger.warning("Not connected to Chroma, skipping schema check")
            return False
        
        try:
            # Get or create the Document collection
            try:
                self._client.get_collection(self.document_collection)
            except Exception:
                self._client.create_collection(
                    embedding_function=self.embedding_function,
                    name=self.document_collection,
                    metadata={"description": "Document collection"}
                )
            
            # Get or create the Chunk collection
            try:
                self._client.get_collection(self.chunk_collection)
            except Exception:
                self._client.create_collection(
                    embedding_function=self.embedding_function,
                    name=self.chunk_collection,
                    metadata={"description": "Chunk collection"}
                )
            
            return True
        except Exception as e:
            logger.error(f"Failed to ensure schema: {e}")
            return False
    
    def batch_upsert_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Batch upsert documents to Chroma."""
        if not self._connected or self._client is None:
            logger.warning("Not connected to Chroma, skipping batch upsert")
            return False
        
        try:
            # Get the collection
            collection = self._client.get_collection(self.document_collection)
            
            # Prepare batch data
            ids = []
            contents = []
            metadatas = []
            
            # Process each document
            for doc in documents:
                doc_id = doc.get("doc_id")
                if not doc_id:
                    logger.warning("Document missing doc_id, skipping")
                    continue
                
                # Add to batch
                ids.append(doc_id)
                contents.append(doc.get("title", ""))
                
                # Prepare metadata
                metadata = {
                    "doc_id": doc_id,
                    "title": doc.get("title", ""),
                    "doc_type": doc.get("doc_type", ""),
                    "jurisdiction": doc.get("jurisdiction", ""),
                    "lang": doc.get("lang", ""),
                    "entities": json.dumps(doc.get("entities", [])),
                    "valid_from": doc.get("valid_from"),
                    "valid_to": doc.get("valid_to"),
                }
                metadatas.append(metadata)
            
            # Upsert to collection
            if ids:
                collection.upsert(
                    ids=ids,
                    documents=contents,
                    metadatas=metadatas
                )
                logger.info(f"Upserted {len(ids)} documents to Chroma")
                return True
            else:
                logger.warning("No valid documents to upsert")
                return False
            
        except Exception as e:
            logger.error(f"Failed to batch upsert documents: {e}")
            return False
    
    def batch_upsert_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """Batch upsert chunks to Chroma."""
        if not self._connected or self._client is None:
            logger.warning("Not connected to Chroma, skipping batch upsert")
            return False
        
        try:
            # Get the collection
            collection = self._client.get_collection(self.chunk_collection)
            # Ensure we use the consistent embedding function
            collection._embedding_function = self.embedding_function
            
            # Prepare batch data
            ids = []
            documents = []
            metadatas = []
            embeddings = []
            
            # Get the embedding function
            embedding_fn = get_default_embeddings()
            
            # Process each chunk
            for chunk in chunks:
                chunk_id = chunk.get("chunk_id")
                if not chunk_id:
                    logger.warning("Chunk missing chunk_id, skipping")
                    continue
                
                # Get the chunk text
                chunk_text = chunk.get("body", "")
                
                # Add to batch
                ids.append(chunk_id)
                documents.append(chunk_text)
                
                # Prepare metadata
                metadata = {
                    "chunk_id": chunk_id,
                    "doc_id": chunk.get("doc_id", ""),
                    "section": chunk.get("section", ""),
                    "entities": json.dumps(chunk.get("entities", [])),
                    "relationships": json.dumps(chunk.get("relationships", {})),
                    "dates": json.dumps(chunk.get("dates", {})),
                    "valid_from": chunk.get("valid_from"),
                    "valid_to": chunk.get("valid_to"),
                }
                metadatas.append(metadata)
                
                # Generate embedding
                if "embedding" in chunk:
                    # Use pre-computed embedding if available
                    embeddings.append(chunk["embedding"])
                else:
                    # Generate embedding for the chunk text
                    try:
                        embedding = embedding_fn.embed_query(chunk_text)
                        embeddings.append(embedding)
                        logger.debug(f"Generated embedding for chunk {chunk_id}")
                    except Exception as e:
                        logger.error(f"Failed to generate embedding for chunk {chunk_id}: {e}")
                        # Don't add this chunk to avoid errors
                        ids.pop()
                        documents.pop()
                        metadatas.pop()
            
            # Upsert to collection
            if ids:
                collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
                logger.info(f"Upserted {len(ids)} chunks to Chroma")
                return True
            else:
                logger.warning("No valid chunks to upsert")
                return False
            
        except Exception as e:
            logger.error(f"Failed to batch upsert chunks: {e}")
            return False
    
    def hybrid_search(self, query: str, alpha: float = None, limit: int = None, where: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Perform a hybrid search (vector + keyword) on the chunk collection."""
        if not self._connected or self._client is None:
            logger.warning("Not connected to Chroma, returning empty results")
            return []
        
        try:
            # Get the collection
            collection = self._client.get_collection(self.chunk_collection)
            # Ensure we use the consistent embedding function
            collection._embedding_function = self.embedding_function
            
            # Set defaults
            if alpha is None:
                alpha = self.default_alpha
            if limit is None:
                limit = self.stage1_limit
            
            # Convert where filter to Chroma format
            where_filter = self._convert_where_filter(where) if where else None
            
            # Perform hybrid search
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_filter,
                include=["metadatas", "documents", "distances"]
            )
            
            # Process results
            processed_results = []
            
            if results and "ids" in results and results["ids"]:
                logger.info(f"Vector search returned {len(results['ids'][0])} results")
                
                for i, doc_id in enumerate(results["ids"][0]):
                    if i < len(results["metadatas"][0]):
                        metadata = results["metadatas"][0][i]
                        document = results["documents"][0][i] if i < len(results["documents"][0]) else ""
                        
                        # Parse entities from JSON string
                        entities = []
                        if "entities" in metadata and metadata["entities"]:
                            try:
                                entities = json.loads(metadata["entities"])
                            except Exception as e:
                                logger.warning(f"Failed to parse entities JSON: {e}")
                        
                        # Parse dates from JSON string
                        dates = {}
                        if "dates" in metadata and metadata["dates"]:
                            try:
                                dates = json.loads(metadata["dates"])
                            except Exception as e:
                                logger.warning(f"Failed to parse dates JSON: {e}")
                        
                        # Parse relationships from JSON string
                        relationships = {}
                        if "relationships" in metadata and metadata["relationships"]:
                            try:
                                relationships = json.loads(metadata["relationships"])
                            except Exception as e:
                                logger.warning(f"Failed to parse relationships JSON: {e}")
                        
                        # Calculate score (1 - distance)
                        score = 0.0
                        if "distances" in results and results["distances"] and i < len(results["distances"][0]):
                            distance = results["distances"][0][i]
                            score = 1.0 - distance if distance <= 1.0 else 0.0
                        
                        processed_results.append({
                            "chunk_id": metadata.get("chunk_id", ""),
                            "doc_id": metadata.get("doc_id", ""),
                            "section": metadata.get("section", ""),
                            "body": document,
                            "entities": entities,
                            "relationships": relationships,
                            "dates": dates,
                            "valid_from": metadata.get("valid_from", ""),
                            "valid_to": metadata.get("valid_to", ""),
                            "score": score,
                            "metadata": {
                                "section": metadata.get("section", ""),
                                "entities": entities,
                                "relationships": relationships,
                                "dates": dates,
                                "valid_from": metadata.get("valid_from", ""),
                                "valid_to": metadata.get("valid_to", ""),
                            }
                        })
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []
    
    def _convert_where_filter(self, where: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Weaviate-style where filter to Chroma format."""
        if not where:
            return {}
        
        chroma_filter = {}
        for key, value in where.items():
            if key == "entities":
                # For entities, we need special handling since they're stored as JSON strings
                continue  # Skip for now, would need more complex filtering
            elif key == "dates":
                # For dates, we need special handling since they're stored as JSON strings
                continue  # Skip for now, would need more complex filtering
            elif isinstance(value, str):
                chroma_filter[key] = value
            elif isinstance(value, list):
                if len(value) == 1:
                    chroma_filter[key] = value[0]
                else:
                    # Chroma doesn't support OR conditions directly in the same way
                    # We'll need to do multiple queries and combine results
                    pass
            elif isinstance(value, dict):
                # Handle date ranges
                if "gte" in value:
                    chroma_filter[f"{key}$gte"] = value["gte"]
                if "lte" in value:
                    chroma_filter[f"{key}$lte"] = value["lte"]
        
        return chroma_filter
    
    def aggregate_group_by(self, facet: str, where: Optional[Dict[str, Any]] = None, limit: int = 100) -> Dict[str, int]:
        """Get facet value counts."""
        if not self._connected or self._client is None:
            logger.warning("Not connected to Chroma, returning empty results")
            return {}
        
        try:
            collection = self._client.get_collection(self.chunk_collection)
            
            # Convert where filter to Chroma format
            where_filter = self._convert_where_filter(where) if where else None
            
            # Get all documents matching the filter
            results = collection.get(where=where_filter, include=["metadatas"])
            
            # Manually aggregate the results
            facet_counts = {}
            
            if results and "metadatas" in results and results["metadatas"]:
                for metadata in results["metadatas"]:
                    if facet in metadata:
                        value = metadata[facet]
                        if value:
                            facet_counts[value] = facet_counts.get(value, 0) + 1
            
            # Sort by count descending and limit
            sorted_counts = dict(sorted(facet_counts.items(), key=lambda x: x[1], reverse=True)[:limit])
            
            return sorted_counts
            
        except Exception as e:
            logger.error(f"Failed to aggregate facet values: {e}")
            return {}
    
    def get_chunk_facets(self) -> List[str]:
        """Get all available facets for chunks."""
        facets = ["doc_type", "section", "jurisdiction", "lang"]
        return facets
    
    def update_chunk_stats(self, chunk_id: str, stats: Dict[str, Any]) -> bool:
        """Update chunk stats."""
        if not self._connected or self._client is None:
            logger.warning("Not connected to Chroma, skipping chunk stats update")
            return False
        
        try:
            # Get or create the ChunkStats collection
            try:
                collection = self._client.get_collection("ChunkStats")
            except Exception:
                # Use a custom embedding function with the default embeddings
                from chromadb.utils import embedding_functions
                import numpy as np
                
                class CustomEmbeddingFunction(embedding_functions.EmbeddingFunction):
                    def __init__(self, dimensions=1024):
                        self.dimensions = dimensions
                    
                    def __call__(self, texts):
                        # Convert single text to list if needed
                        if isinstance(texts, str):
                            texts = [texts]
                        
                        try:
                            # Try to use the default embeddings from the config
                            from configs.load import get_default_embeddings
                            embedding_model = get_default_embeddings()
                            return embedding_model.embed_documents(texts)
                        except Exception as e:
                            logger.warning(f"Error generating embeddings: {e}")
                            # Return random vectors with 1024 dimensions as a fallback
                            return [list(np.random.normal(0, 0.1, self.dimensions)) for _ in texts]
                
                embedding_function = CustomEmbeddingFunction(dimensions=1024)
                
                collection = self._client.create_collection(
                    name="ChunkStats",
                    embedding_function=embedding_function,
                    metadata={"description": "Chunk statistics"}
                )
            
            # Use the default embeddings from the config
            from configs.load import get_default_embeddings
            import numpy as np
            
            try:
                # Try to use the default embeddings model (BGE-M3)
                embedding_model = get_default_embeddings()
                embedding = embedding_model.embed_query(chunk_id)
            except Exception as e:
                logger.warning(f"Error generating embedding with default model: {e}")
                # Fall back to a random vector with 1024 dimensions
                embedding = list(np.random.normal(0, 0.1, 1024))
            
            # Prepare metadata
            metadata = {
                "chunk_id": chunk_id,
                "useful_count": stats.get("useful_count", 0),
                "last_useful_at": stats.get("last_useful_at", ""),
                "decayed_utility": stats.get("decayed_utility", 0.0)
            }
            
            # Upsert to collection
            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[chunk_id]  # Use chunk_id as document content
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update chunk stats: {e}")
            return False
    def upsert_facet_value_vector(self, facet: str, value: str, vector: List[float], aliases: Optional[List[str]] = None) -> bool:
        """Upsert a facet-value vector."""
        if not self._connected or self._client is None:
            logger.warning("Not connected to Chroma, skipping facet vector upsert")
            return False
        
        try:
            # Get or create the FacetValueVector collection
            try:
                collection = self._client.get_collection("FacetValueVector")
            except Exception:
                collection = self._client.create_collection(
                    name="FacetValueVector",
                    metadata={"description": "Facet value vectors"}
                )
            
            # Create a unique ID for this facet-value pair
            facet_value_id = f"{facet}:{value}"
            
            # Prepare metadata
            metadata = {
                "facet": facet,
                "value": value,
                "aliases": json.dumps(aliases or []),
                "updated_at": datetime.now().isoformat()
            }
            
            # Upsert to collection
            collection.upsert(
                ids=[facet_value_id],
                embeddings=[vector],
                metadatas=[metadata],
                documents=[value]  # Use value as document content
            )
            
            logger.debug(f"Upserted facet-value vector for {facet}={value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert facet-value vector: {e}")
            return False
            
    def get_facet_vectors(self, facet: str) -> List[Dict[str, Any]]:
        """Get all facet-value vectors for a specific facet."""
        if not self._connected or self._client is None:
            logger.warning("Not connected to Chroma, returning empty facet vectors")
            return []
        
        try:
            # Get the FacetValueVector collection
            try:
                collection = self._client.get_collection("FacetValueVector")
            except Exception:
                logger.warning("FacetValueVector collection does not exist")
                return []
            
            # Query for all vectors with this facet
            where_filter = {"facet": facet}
            results = collection.get(
                where=where_filter,
                include=["embeddings", "metadatas", "documents"]
            )
            
            # Process results
            vectors = []
            if results and results["ids"]:
                for i, id_val in enumerate(results["ids"]):
                    if i < len(results["metadatas"]) and i < len(results["embeddings"]):
                        metadata = results["metadatas"][i]
                        embedding = results["embeddings"][i]
                        
                        # Parse aliases from JSON string
                        aliases = []
                        if "aliases" in metadata and metadata["aliases"]:
                            try:
                                aliases = json.loads(metadata["aliases"])
                            except json.JSONDecodeError:
                                pass
                        
                        vectors.append({
                            "id": id_val,
                            "facet": metadata.get("facet", facet),
                            "value": metadata.get("value", ""),
                            "vector": embedding,
                            "aliases": aliases
                        })
            
            return vectors
            
        except Exception as e:
            logger.error(f"Failed to get facet vectors: {e}")
            return []