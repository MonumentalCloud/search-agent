import os
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

try:
    import weaviate
    from weaviate.classes.config import Property, DataType, Configure
    from weaviate.classes.query import MetadataQuery, Filter
except Exception:  # pragma: no cover - allow import in environments without weaviate installed yet
    weaviate = None
    Property = None
    DataType = None
    Configure = None
    MetadataQuery = None
    Filter = None

from configs.load import load_yaml_config

logger = logging.getLogger(__name__)


class WeaviateClient:
    def __init__(self) -> None:
        cfg = load_yaml_config(os.path.join(os.path.dirname(__file__), "..", "configs", "default.yaml"))
        wcfg = cfg["search_backend"]["weaviate"]
        self.endpoint: str = wcfg.get("endpoint", "http://localhost:8080")
        self.api_key: Optional[str] = os.environ.get("WEAVIATE_KEY") or wcfg.get("api_key")
        self.document_class: str = wcfg["classes"]["document"]
        self.chunk_class: str = wcfg["classes"]["chunk"]
        self.default_alpha: float = float(wcfg.get("default_alpha", 0.5))
        self.stage1_limit: int = int(wcfg.get("stage1_limit", 300))
        self.stage3_limit: int = int(wcfg.get("stage3_limit", 200))
        self._client = None
        self._connected = False
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to Weaviate."""
        if weaviate is not None:
            try:
                # Try v4 client first
                if hasattr(weaviate, "connect_to_local"):
                    self._client = weaviate.connect_to_local(host="localhost", port=8080)
                elif hasattr(weaviate, "connect_to_weaviate_cloud"):
                    self._client = weaviate.connect_to_weaviate_cloud(self.endpoint, self.api_key)
                else:
                    # Fallback to v3 client
                    self._client = weaviate.Client(self.endpoint)
                self._connected = True
                logger.info(f"Connected to Weaviate at {self.endpoint}")
            except Exception as e:
                logger.warning(f"Could not connect to Weaviate: {e}")
                self._connected = False
    
    def close(self) -> None:
        """Close the Weaviate connection."""
        if self._client is not None:
            try:
                if hasattr(self._client, 'close'):
                    self._client.close()
                elif hasattr(self._client, 'disconnect'):
                    self._client.disconnect()
                logger.info("Closed Weaviate connection")
            except Exception as e:
                logger.warning(f"Error closing Weaviate connection: {e}")
            finally:
                self._client = None
                self._connected = False
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Destructor to ensure connection is closed."""
        if hasattr(self, '_client'):
            self.close()
        
    def _format_rfc3339_date(self, date_str: str) -> str:
        """Format a date string to RFC3339 format for Weaviate.
        
        Args:
            date_str: A date string in ISO format
            
        Returns:
            str: The date string in RFC3339 format with Z suffix
        """
        # If already has Z suffix, return as is
        if date_str.endswith('Z'):
            return date_str
            
        # Check if it's already in ISO format
        iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2})?$'
        if re.match(iso_pattern, date_str):
            # Add Z suffix for UTC
            return f"{date_str}Z"
            
        # Try to parse as datetime and convert to ISO
        try:
            dt = datetime.fromisoformat(date_str)
            return f"{dt.isoformat()}Z"
        except ValueError:
            # If all else fails, return current time
            return f"{datetime.now().isoformat()}Z"

    def ensure_schema(self) -> bool:
        """Create Document and Chunk classes with proper filterable fields."""
        if not self._connected or self._client is None:
            logger.error("Not connected to Weaviate")
            return False
        
        try:
            # Document class
            document_properties = [
                Property(name="doc_id", data_type=DataType.TEXT, filterable=True),
                Property(name="title", data_type=DataType.TEXT),
                Property(name="doc_type", data_type=DataType.TEXT, filterable=True),
                Property(name="jurisdiction", data_type=DataType.TEXT, filterable=True),
                Property(name="lang", data_type=DataType.TEXT, filterable=True),
                Property(name="valid_from", data_type=DataType.DATE, filterable=True),
                Property(name="valid_to", data_type=DataType.DATE, filterable=True),
                Property(name="entities", data_type=DataType.TEXT_ARRAY, filterable=True),
            ]
            
            # Chunk class
            chunk_properties = [
                Property(name="chunk_id", data_type=DataType.TEXT, filterable=True),
                Property(name="doc_id", data_type=DataType.TEXT, filterable=True),
                Property(name="section", data_type=DataType.TEXT, filterable=True),
                Property(name="body", data_type=DataType.TEXT),
                Property(name="entities", data_type=DataType.TEXT_ARRAY, filterable=True),
                Property(name="valid_from", data_type=DataType.DATE, filterable=True),
                Property(name="valid_to", data_type=DataType.DATE, filterable=True),
                Property(name="created_at", data_type=DataType.DATE, filterable=True),
                Property(name="updated_at", data_type=DataType.DATE, filterable=True),
            ]
            
            # Create classes if they don't exist
            if not self._client.collections.exists(self.document_class):
                self._client.collections.create(
                    name=self.document_class,
                    properties=document_properties,
                    vectorizer_config=Configure.Vectorizer.none(),  # External embeddings
                )
                logger.info(f"Created Document class: {self.document_class}")
            
            if not self._client.collections.exists(self.chunk_class):
                self._client.collections.create(
                    name=self.chunk_class,
                    properties=chunk_properties,
                    vectorizer_config=Configure.Vectorizer.none(),  # External embeddings
                )
                logger.info(f"Created Chunk class: {self.chunk_class}")
            
            # Create side classes
            self._ensure_side_classes()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create schema: {e}")
            return False

    def _ensure_side_classes(self) -> None:
        """Create FacetValueVector and ChunkStats side classes."""
        try:
            # FacetValueVector class
            facet_vector_properties = [
                Property(name="facet", data_type=DataType.TEXT, filterable=True),
                Property(name="value", data_type=DataType.TEXT, filterable=True),
                Property(name="aliases", data_type=DataType.TEXT_ARRAY),
                Property(name="embedding", data_type=DataType.NUMBER_ARRAY),
                Property(name="updated_at", data_type=DataType.DATE, filterable=True),
            ]
            
            if not self._client.collections.exists("FacetValueVector"):
                self._client.collections.create(
                    name="FacetValueVector",
                    properties=facet_vector_properties,
                    vectorizer_config=Configure.Vectorizer.none(),
                )
                logger.info("Created FacetValueVector class")
            
            # ChunkStats class
            chunk_stats_properties = [
                Property(name="chunk_id", data_type=DataType.TEXT, filterable=True),
                Property(name="useful_count", data_type=DataType.INT),
                Property(name="last_useful_at", data_type=DataType.DATE, filterable=True),
                Property(name="intent_hist", data_type=DataType.TEXT),
                Property(name="entity_hist", data_type=DataType.TEXT),
                Property(name="query_centroid", data_type=DataType.NUMBER_ARRAY),
                Property(name="decayed_utility", data_type=DataType.NUMBER),
            ]
            
            if not self._client.collections.exists("ChunkStats"):
                self._client.collections.create(
                    name="ChunkStats",
                    properties=chunk_stats_properties,
                    vectorizer_config=Configure.Vectorizer.none(),
                )
                logger.info("Created ChunkStats class")
                
        except Exception as e:
            logger.warning(f"Could not create side classes: {e}")

    def batch_upsert_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Batch upsert Document objects."""
        if not self._connected or self._client is None:
            logger.error("Not connected to Weaviate")
            return False
        
        try:
            collection = self._client.collections.get(self.document_class)
            
            # Prepare documents for batch insert
            objects = []
            for doc in documents:
                obj = {
                    "doc_id": doc.get("doc_id", ""),
                    "title": doc.get("title", ""),
                    "doc_type": doc.get("doc_type"),
                    "jurisdiction": doc.get("jurisdiction"),
                    "lang": doc.get("lang"),
                    "valid_from": doc.get("valid_from") + "Z" if doc.get("valid_from") else None,
                    "valid_to": doc.get("valid_to") + "Z" if doc.get("valid_to") else None,
                    "entities": doc.get("entities", []),
                }
                objects.append(obj)
            
            # Batch insert
            collection.data.insert_many(objects)
            logger.info(f"Upserted {len(documents)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert documents: {e}")
            return False

    def batch_upsert_chunks(self, chunks: List[Dict[str, Any]], vectors: Optional[List[List[float]]] = None) -> bool:
        """Batch upsert Chunk objects with optional vectors."""
        if not self._connected or self._client is None:
            logger.error("Not connected to Weaviate")
            return False
        
        try:
            collection = self._client.collections.get(self.chunk_class)
            
            # Generate vectors if not provided
            if vectors is None:
                try:
                    from configs.load import get_default_embeddings
                    embeddings_model = get_default_embeddings()
                    vectors = []
                    for chunk in chunks:
                        # Create embedding from chunk body
                        vector = embeddings_model.embed_query(chunk.get("body", ""))
                        vectors.append(vector)
                    logger.info(f"Generated {len(vectors)} vectors for chunks")
                except Exception as e:
                    logger.warning(f"Could not generate vectors (will store without vectors): {e}")
                    vectors = []  # Store without vectors
            
            # Prepare chunks for batch insert using DataObject for vectors
            from weaviate.classes.data import DataObject
            
            objects = []
            for i, chunk in enumerate(chunks):
                properties = {
                    "chunk_id": chunk.get("chunk_id", ""),
                    "doc_id": chunk.get("doc_id", ""),
                    "section": chunk.get("section"),
                    "body": chunk.get("body", ""),
                    "entities": chunk.get("entities", []),
                    "valid_from": chunk.get("valid_from") + "Z" if chunk.get("valid_from") else None,
                    "valid_to": chunk.get("valid_to") + "Z" if chunk.get("valid_to") else None,
                    "created_at": self._format_rfc3339_date(chunk.get("created_at") or datetime.now().isoformat()),
                    "updated_at": self._format_rfc3339_date(chunk.get("updated_at") or datetime.now().isoformat()),
                }
                
                # Create DataObject with vector if available
                if vectors and i < len(vectors):
                    obj = DataObject(properties=properties, vector=vectors[i])
                else:
                    obj = DataObject(properties=properties)
                
                objects.append(obj)
            
            # Batch insert
            collection.data.insert_many(objects)
            logger.info(f"Upserted {len(chunks)} chunks with vectors")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert chunks: {e}")
            return False

    def hybrid_search(self, query: str, alpha: float, limit: int, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Hybrid search with BM25 + vector similarity."""
        if not self._connected or self._client is None:
            logger.warning("Not connected to Weaviate, returning empty results")
            return []
        
        try:
            collection = self._client.collections.get(self.chunk_class)
            
            # Build where filter
            where_filter = None
            if where:
                where_filter = self._build_where_filter(where)
            
            # Generate query vector for hybrid search
            try:
                from configs.load import get_default_embeddings
                embeddings_model = get_default_embeddings()
                query_vector = embeddings_model.embed_query(query)
                
                # Perform hybrid search with vector (without where filter for now)
                response = collection.query.hybrid(
                    query=query,
                    alpha=alpha,
                    vector=query_vector,  # Ensure vector is passed
                    limit=limit,
                    return_metadata=MetadataQuery(score=True),
                    return_properties=["chunk_id", "doc_id", "section", "body", "entities", "valid_from", "valid_to"]
                )
            except Exception as e:
                logger.warning(f"Could not generate query vector, falling back to BM25: {e}")
                # Fallback to BM25 search (without where filter for now)
                response = collection.query.bm25(
                    query=query,
                    limit=limit,
                    return_metadata=MetadataQuery(score=True),
                    return_properties=["chunk_id", "doc_id", "section", "body", "entities", "valid_from", "valid_to"]
                )
            
            results = []
            for obj in response.objects:
                results.append({
                    "chunk_id": obj.properties.get("chunk_id", ""),
                    "doc_id": obj.properties.get("doc_id", ""),
                    "section": obj.properties.get("section"),
                    "body": obj.properties.get("body", ""),
                    "entities": obj.properties.get("entities", []),
                    "valid_from": obj.properties.get("valid_from"),
                    "valid_to": obj.properties.get("valid_to"),
                    "score": obj.metadata.score if obj.metadata else 0.0,
                    "metadata": {
                        "section": obj.properties.get("section"),
                        "entities": obj.properties.get("entities", []),
                        "valid_from": obj.properties.get("valid_from"),
                        "valid_to": obj.properties.get("valid_to"),
                    }
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []

    def aggregate_group_by(self, facet: str, where: Optional[Dict[str, Any]] = None, limit: int = 100) -> Dict[str, int]:
        """Aggregate counts by facet value."""
        if not self._connected or self._client is None:
            return {}
        
        try:
            collection = self._client.collections.get(self.chunk_class)
            
            where_filter = None
            if where:
                where_filter = self._build_where_filter(where)
            
            # Note: over_all doesn't support where filter or return_meta_count in current client version
            response = collection.aggregate.over_all(
                group_by=facet  # Pass as string, not Filter.by_property(facet)
            )
            
            counts = {}
            for group in response.groups:
                if group.grouped_by and group.total_count:
                    value = group.grouped_by.get("value")
                    if value:
                        counts[value] = group.total_count
            
            return counts
            
        except Exception as e:
            logger.error(f"Aggregate failed: {e}")
            return {}

    def _build_where_filter(self, where: Dict[str, Any]) -> Filter:
        """Build Weaviate where filter from dict."""
        if not where:
            return None
        
        filters = []
        for key, value in where.items():
            if isinstance(value, str):
                filters.append(Filter.by_property(key).equal(value))
            elif isinstance(value, list):
                filters.append(Filter.by_property(key).contains_any(value))
            elif isinstance(value, dict):
                # Handle date ranges
                if "gte" in value:
                    filters.append(Filter.by_property(key).greater_than_equal(value["gte"]))
                if "lte" in value:
                    filters.append(Filter.by_property(key).less_than_equal(value["lte"]))
        
        if len(filters) == 1:
            return filters[0]
        elif len(filters) > 1:
            return Filter.all_of(filters)
        
        return None

    def upsert_facet_value_vector(self, facet: str, value: str, vector: List[float], aliases: List[str] = None) -> bool:
        """Upsert a facet-value vector."""
        if not self._connected or self._client is None:
            return False
        
        try:
            collection = self._client.collections.get("FacetValueVector")
            from weaviate.classes.data import DataObject
            
            # First, try to find existing record
            try:
                existing_records = collection.query.fetch_objects(
                    filters=Filter.by_property("facet").equal(facet).and_(
                        Filter.by_property("value").equal(value)
                    ),
                    limit=1
                )
                
                # If record exists, delete it first
                if existing_records and len(existing_records.objects) > 0:
                    try:
                        # Get the UUID of the existing record
                        existing_uuid = existing_records.objects[0].uuid
                        # Delete the existing record
                        collection.data.delete_by_id(existing_uuid)
                        logger.debug(f"Deleted existing facet vector for {facet}:{value}")
                    except Exception as delete_err:
                        logger.warning(f"Could not delete existing facet vector: {delete_err}")
            except Exception as query_err:
                logger.warning(f"Could not query existing facet vectors: {query_err}")
            
            obj = {
                "facet": facet,
                "value": value,
                "aliases": aliases or [],
                "embedding": vector,
                "updated_at": datetime.now().isoformat(),
            }
            
            # Insert the new record directly with properties
            collection.data.insert(obj)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert facet vector: {e}")
            return False

    def get_facet_vectors(self, facet: str) -> List[Dict[str, Any]]:
        """Get all facet-value vectors for a facet."""
        if not self._connected or self._client is None:
            return []
        
        try:
            collection = self._client.collections.get("FacetValueVector")
            
            # Note: fetch_objects doesn't support where filter in current client version
            # We'll fetch all and filter in Python for now
            response = collection.query.fetch_objects(
                return_properties=["facet", "value", "aliases", "embedding", "updated_at"]
            )
            
            vectors = []
            for obj in response.objects:
                # Filter by facet in Python since where filter isn't supported
                if obj.properties.get("facet") == facet:
                    vectors.append({
                        "facet": obj.properties.get("facet"),
                        "value": obj.properties.get("value"),
                        "aliases": obj.properties.get("aliases", []),
                        "vector": obj.properties.get("embedding", []),
                        "updated_at": obj.properties.get("updated_at"),
                    })
            
            return vectors
            
        except Exception as e:
            logger.error(f"Failed to get facet vectors: {e}")
            return []

    def get_chunk_facets(self) -> List[str]:
        """Fetch all filterable properties (facets) for the chunk class from the schema."""
        if not self._connected or self._client is None:
            logger.warning("Not connected to Weaviate, cannot fetch facets.")
            return []
        try:
            schema = self._client.collections.get(self.chunk_class).config.as_dict()
            properties = schema.get("properties", [])
            facets = [prop["name"] for prop in properties if prop.get("filterable")]
            logger.debug(f"Discovered chunk facets: {facets}")
            return facets
        except Exception as e:
            logger.error(f"Failed to fetch chunk facets: {e}")
            return []
            
    def update_chunk_stats(self, chunk_id: str, stats_dict: Dict[str, Any]) -> bool:
        """Update statistics for a chunk in the ChunkStats collection.
        
        Args:
            chunk_id: The ID of the chunk to update stats for
            stats_dict: Dictionary containing stats to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self._connected or self._client is None:
            logger.error("Not connected to Weaviate")
            return False
        
        try:
            # Get the ChunkStats collection
            if not self._client.collections.exists("ChunkStats"):
                logger.warning("ChunkStats collection does not exist, creating it")
                self._ensure_side_classes()
            
            collection = self._client.collections.get("ChunkStats")
            
            # Check if a record already exists for this chunk_id
            from weaviate.classes.query import Filter
            from weaviate.classes.data import DataObject
            
            # First, try to find existing record
            try:
                existing_records = collection.query.fetch_objects(
                    filters=Filter.by_property("chunk_id").equal(chunk_id),
                    limit=1
                )
                
                # If record exists, delete it first
                if existing_records and len(existing_records.objects) > 0:
                    try:
                        # Get the UUID of the existing record
                        existing_uuid = existing_records.objects[0].uuid
                        # Delete the existing record
                        collection.data.delete_by_id(existing_uuid)
                        logger.debug(f"Deleted existing stats record for chunk {chunk_id}")
                    except Exception as delete_err:
                        logger.warning(f"Could not delete existing record: {delete_err}")
            except Exception as query_err:
                logger.warning(f"Could not query existing records: {query_err}")
            
            # Prepare the data to insert
            properties = {
                "chunk_id": chunk_id,
                **stats_dict
            }
            
            # Convert any non-serializable types
            if "query_clusters" in properties:
                # Convert QueryCluster objects to dictionaries
                if isinstance(properties["query_clusters"], list):
                    properties["query_clusters"] = [
                        {
                            "centroid": cluster.centroid if hasattr(cluster, "centroid") else cluster.get("centroid", []),
                            "count": cluster.count if hasattr(cluster, "count") else cluster.get("count", 0),
                            "last_updated": cluster.last_updated if hasattr(cluster, "last_updated") else cluster.get("last_updated", ""),
                            "sample_queries": cluster.sample_queries if hasattr(cluster, "sample_queries") else cluster.get("sample_queries", [])
                        }
                        for cluster in properties["query_clusters"]
                    ]
            
            # Insert the new record directly with properties
            collection.data.insert(properties)
            
            logger.info(f"Updated stats for chunk {chunk_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update chunk stats: {e}")
            return False

    def delete_all_data(self) -> bool:
        """Delete all data from all collections."""
        if not self._connected or self._client is None:
            logger.error("Not connected to Weaviate")
            return False
        
        try:
            # List of all collections to clear
            collections_to_clear = [
                self.document_class,
                self.chunk_class,
                "FacetValueVector",
                "ChunkStats"
            ]
            
            cleared_count = 0
            for collection_name in collections_to_clear:
                try:
                    if self._client.collections.exists(collection_name):
                        collection = self._client.collections.get(collection_name)
                        # Delete all objects in the collection
                        collection.data.delete_many()
                        logger.info(f"Cleared collection: {collection_name}")
                        cleared_count += 1
                    else:
                        logger.info(f"Collection {collection_name} does not exist, skipping")
                except Exception as e:
                    logger.warning(f"Failed to clear collection {collection_name}: {e}")
            
            logger.info(f"Successfully cleared {cleared_count} collections")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete all data: {e}")
            return False

    def reset_database(self) -> bool:
        """Reset the entire database by deleting all collections and recreating schema."""
        if not self._connected or self._client is None:
            logger.error("Not connected to Weaviate")
            return False
        
        try:
            # List of all collections to delete
            collections_to_delete = [
                self.document_class,
                self.chunk_class,
                "FacetValueVector",
                "ChunkStats"
            ]
            
            # Delete existing collections
            deleted_count = 0
            for collection_name in collections_to_delete:
                try:
                    if self._client.collections.exists(collection_name):
                        self._client.collections.delete(collection_name)
                        logger.info(f"Deleted collection: {collection_name}")
                        deleted_count += 1
                    else:
                        logger.info(f"Collection {collection_name} does not exist, skipping")
                except Exception as e:
                    logger.warning(f"Failed to delete collection {collection_name}: {e}")
            
            logger.info(f"Successfully deleted {deleted_count} collections")
            
            # Recreate schema
            if self.ensure_schema():
                logger.info("Successfully recreated database schema")
                return True
            else:
                logger.error("Failed to recreate database schema")
                return False
            
        except Exception as e:
            logger.error(f"Failed to reset database: {e}")
            return False