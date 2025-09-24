"""
Retrieval cache for document search results.

This module provides a cache for storing search results to avoid redundant retrievals
when asking questions about the same documents repeatedly.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
import json
import hashlib

logger = logging.getLogger(__name__)

class RetrievalCache:
    """Cache for document retrieval results to improve efficiency."""
    
    def __init__(self, max_cache_size: int = 100, cache_ttl_minutes: int = 60):
        """
        Initialize the retrieval cache.
        
        Args:
            max_cache_size: Maximum number of queries to cache
            cache_ttl_minutes: Time-to-live for cache entries in minutes
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._query_to_chunks: Dict[str, Set[str]] = {}  # Maps query hash to chunk IDs
        self._chunk_to_queries: Dict[str, Set[str]] = {}  # Maps chunk ID to query hashes
        self._last_access: Dict[str, datetime] = {}  # Last access time for LRU eviction
        
        # Load config
        try:
            from configs.load import load_yaml_config
            import os
            
            config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "default.yaml")
            config = load_yaml_config(config_path)
            
            memory_config = config.get("memory", {})
            cache_config = memory_config.get("retrieval_cache", {})
            
            self._max_cache_size = cache_config.get("max_size", max_cache_size)
            cache_ttl = cache_config.get("ttl_minutes", cache_ttl_minutes)
            self._cache_ttl = timedelta(minutes=cache_ttl)
            
            logger.info(f"Initialized retrieval cache with max_size={self._max_cache_size}, ttl={cache_ttl} minutes")
        except Exception as e:
            logger.warning(f"Failed to load cache config, using defaults: {e}")
            self._max_cache_size = max_cache_size
            self._cache_ttl = timedelta(minutes=cache_ttl_minutes)
    
    def _generate_query_hash(self, query: str, facets: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a hash for a query and its facets.
        
        Args:
            query: The search query
            facets: Optional facets used in the search
            
        Returns:
            A hash string that uniquely identifies this query + facets combination
        """
        # Combine query and facets into a single string for hashing
        facets_str = json.dumps(facets, sort_keys=True) if facets else "{}"
        combined = f"{query}|{facets_str}"
        
        # Generate a hash
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def get_cached_results(self, query: str, facets: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached search results for a query if available.
        
        Args:
            query: The search query
            facets: Optional facets used in the search
            
        Returns:
            Cached search results or None if not in cache or expired
        """
        query_hash = self._generate_query_hash(query, facets)
        
        # Check if in cache and not expired
        if query_hash in self._cache:
            cache_entry = self._cache[query_hash]
            cached_time = datetime.fromisoformat(cache_entry["timestamp"])
            
            # Check if cache entry has expired
            if datetime.now() - cached_time > self._cache_ttl:
                # Remove expired entry
                self._remove_cache_entry(query_hash)
                return None
            
            # Update last access time for LRU
            self._last_access[query_hash] = datetime.now()
            
            logger.info(f"Cache hit for query: {query[:30]}... (hash: {query_hash[:8]})")
            return cache_entry["results"]
        
        logger.info(f"Cache miss for query: {query[:30]}...")
        return None
    
    def cache_results(self, query: str, results: List[Dict[str, Any]], facets: Optional[Dict[str, Any]] = None) -> None:
        """
        Cache search results for a query.
        
        Args:
            query: The search query
            results: The search results to cache
            facets: Optional facets used in the search
        """
        query_hash = self._generate_query_hash(query, facets)
        
        # Ensure we don't exceed max cache size (use LRU eviction)
        if len(self._cache) >= self._max_cache_size and query_hash not in self._cache:
            self._evict_lru_entry()
        
        # Extract chunk IDs from results
        chunk_ids = set()
        for result in results:
            chunk_id = result.get("chunk_id")
            if chunk_id:
                chunk_ids.add(chunk_id)
                
                # Update chunk_to_queries mapping
                if chunk_id not in self._chunk_to_queries:
                    self._chunk_to_queries[chunk_id] = set()
                self._chunk_to_queries[chunk_id].add(query_hash)
        
        # Store the cache entry
        self._cache[query_hash] = {
            "query": query,
            "facets": facets,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
        # Update query_to_chunks mapping
        self._query_to_chunks[query_hash] = chunk_ids
        
        # Update last access time
        self._last_access[query_hash] = datetime.now()
        
        logger.info(f"Cached results for query: {query[:30]}... ({len(results)} chunks)")
    
    def invalidate_for_chunk(self, chunk_id: str) -> None:
        """
        Invalidate all cache entries that contain a specific chunk.
        
        Args:
            chunk_id: The chunk ID to invalidate cache entries for
        """
        if chunk_id not in self._chunk_to_queries:
            return
        
        # Get all query hashes that reference this chunk
        query_hashes = self._chunk_to_queries[chunk_id].copy()
        
        # Remove each cache entry
        for query_hash in query_hashes:
            self._remove_cache_entry(query_hash)
        
        logger.info(f"Invalidated {len(query_hashes)} cache entries for chunk: {chunk_id}")
    
    def _remove_cache_entry(self, query_hash: str) -> None:
        """
        Remove a cache entry and update mappings.
        
        Args:
            query_hash: The query hash to remove
        """
        if query_hash not in self._cache:
            return
        
        # Get chunk IDs for this query
        chunk_ids = self._query_to_chunks.get(query_hash, set())
        
        # Remove query from chunk_to_queries mappings
        for chunk_id in chunk_ids:
            if chunk_id in self._chunk_to_queries:
                self._chunk_to_queries[chunk_id].discard(query_hash)
                if not self._chunk_to_queries[chunk_id]:
                    del self._chunk_to_queries[chunk_id]
        
        # Remove from cache and mappings
        del self._cache[query_hash]
        if query_hash in self._query_to_chunks:
            del self._query_to_chunks[query_hash]
        if query_hash in self._last_access:
            del self._last_access[query_hash]
    
    def _evict_lru_entry(self) -> None:
        """Evict the least recently used cache entry."""
        if not self._last_access:
            return
        
        # Find the least recently used entry
        lru_query_hash = min(self._last_access.items(), key=lambda x: x[1])[0]
        
        # Remove it
        self._remove_cache_entry(lru_query_hash)
        logger.debug(f"Evicted LRU cache entry: {lru_query_hash[:8]}")
    
    def clear_cache(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()
        self._query_to_chunks.clear()
        self._chunk_to_queries.clear()
        self._last_access.clear()
        logger.info("Retrieval cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "size": len(self._cache),
            "max_size": self._max_cache_size,
            "ttl_minutes": self._cache_ttl.total_seconds() / 60,
            "unique_chunks": len(self._chunk_to_queries)
        }


# Global instance for easy access
retrieval_cache = RetrievalCache()
