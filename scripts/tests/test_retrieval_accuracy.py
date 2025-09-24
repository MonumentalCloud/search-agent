#!/usr/bin/env python3
"""
Script to test the retrieval accuracy of the search agent on the BEIR FiQA dataset.
Tests both immediate chunk retrieval and retrieval after processing through the agent.
"""

import os
import json
import logging
import argparse
from typing import Dict, List, Any, Optional, Tuple
import time
import numpy as np
from tqdm import tqdm

import weaviate
from beir.retrieval.evaluation import EvaluateRetrieval

# Add project root to path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters.chunk_retriever import ChunkRetriever
from agent.graph import run_graph

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
CORPUS_CLASS = "FiQACorpus"
QUERY_CLASS = "FiQAQuery"
METRICS = ["ndcg@10", "map@10", "recall@10", "precision@10"]

def load_qrels(qrels_path: str) -> Dict[str, Dict[str, int]]:
    """
    Load relevance judgments from a JSON file.
    
    Args:
        qrels_path: Path to the qrels JSON file
        
    Returns:
        Dictionary of query ID to document ID to relevance score
    """
    logger.info(f"Loading relevance judgments from {qrels_path}")
    
    with open(qrels_path, 'r') as f:
        qrels = json.load(f)
    
    logger.info(f"Loaded {len(qrels)} relevance judgments")
    
    return qrels

def direct_weaviate_retrieval(client: Any, queries: Dict[str, str], top_k: int = 10) -> Dict[str, Dict[str, float]]:
    """
    Retrieve documents directly from Weaviate using vector search.
    
    Args:
        client: Weaviate client
        queries: Dictionary of query ID to query text
        top_k: Number of documents to retrieve
        
    Returns:
        Dictionary of query ID to document ID to score
    """
    logger.info(f"Performing direct Weaviate retrieval for {len(queries)} queries")
    
    # Load the embeddings from config
    from configs.load import get_default_embeddings
    embeddings = get_default_embeddings()
    
    results = {}
    
    for query_id, query_text in tqdm(queries.items(), desc="Direct retrieval"):
        try:
            # Generate embedding for the query
            query_embedding = embeddings.embed_query(query_text)
            
            # Perform vector search
            vector_search = (
                client.query
                .get(CORPUS_CLASS, ["doc_id", "title"])
                .with_near_vector({"vector": query_embedding})
                .with_limit(top_k)
                .do()
            )
            
            # Extract results
            docs = vector_search["data"]["Get"][CORPUS_CLASS]
            query_results = {}
            
            for i, doc in enumerate(docs):
                doc_id = doc["doc_id"]
                # Use 1 - i/top_k as the score (higher is better)
                score = 1.0 - (i / top_k)
                query_results[doc_id] = score
            
            results[query_id] = query_results
            
        except Exception as e:
            logger.error(f"Error retrieving results for query {query_id}: {e}")
            results[query_id] = {}
    
    return results

def agent_based_retrieval(queries: Dict[str, str], top_k: int = 10) -> Dict[str, Dict[str, float]]:
    """
    Retrieve documents using the search agent.
    
    Args:
        queries: Dictionary of query ID to query text
        top_k: Number of documents to retrieve
        
    Returns:
        Dictionary of query ID to document ID to score
    """
    logger.info(f"Performing agent-based retrieval for {len(queries)} queries")
    
    results = {}
    
    for query_id, query_text in tqdm(queries.items(), desc="Agent retrieval"):
        try:
            # Run the query through the agent
            trace_id = f"test-{query_id}"
            agent_result = run_graph(query=query_text, time_hint=None, lang=None, trace_id=trace_id)
            
            # Extract citations
            citations = agent_result.get("citations", [])
            query_results = {}
            
            for i, citation in enumerate(citations[:top_k]):
                doc_id = citation.get("doc_id")
                if doc_id:
                    # Use 1 - i/top_k as the score (higher is better)
                    score = 1.0 - (i / top_k)
                    query_results[doc_id] = score
            
            results[query_id] = query_results
            
        except Exception as e:
            logger.error(f"Error retrieving results for query {query_id}: {e}")
            results[query_id] = {}
    
    return results

def evaluate_results(results: Dict[str, Dict[str, float]], qrels: Dict[str, Dict[str, int]]) -> Dict[str, float]:
    """
    Evaluate retrieval results using BEIR metrics.
    
    Args:
        results: Dictionary of query ID to document ID to score
        qrels: Dictionary of query ID to document ID to relevance score
        
    Returns:
        Dictionary of metric name to score
    """
    logger.info("Evaluating retrieval results")
    
    # Initialize evaluator
    evaluator = EvaluateRetrieval()
    
    # Evaluate results
    metrics = evaluator.evaluate(qrels, results, METRICS)
    
    return metrics

def main():
    parser = argparse.ArgumentParser(description="Test retrieval accuracy on BEIR FiQA dataset")
    parser.add_argument("--data-path", default="data/fiqa", help="Path to the dataset")
    parser.add_argument("--top-k", type=int, default=10, help="Number of documents to retrieve")
    parser.add_argument("--weaviate-url", default="http://localhost:8080", help="Weaviate URL")
    parser.add_argument("--test-size", type=int, default=100, help="Number of queries to test (0 for all)")
    parser.add_argument("--config", default="default.yaml", help="Config file to use for embeddings")
    parser.add_argument("--skip-agent", action="store_true", help="Skip agent-based retrieval test")
    args = parser.parse_args()
    
    # Load queries and qrels
    qrels_path = os.path.join(args.data_path, "fiqa", "qrels.json")
    queries_path = os.path.join(args.data_path, "fiqa", "queries.jsonl")
    
    # Load qrels
    qrels = load_qrels(qrels_path)
    
    # Load queries
    queries = {}
    with open(queries_path, 'r') as f:
        for line in f:
            data = json.loads(line)
            queries[data["_id"]] = data["text"]
    
    # Limit test size if specified
    if args.test_size > 0 and args.test_size < len(queries):
        logger.info(f"Limiting test to {args.test_size} queries")
        query_ids = list(queries.keys())[:args.test_size]
        queries = {qid: queries[qid] for qid in query_ids}
        qrels = {qid: qrels[qid] for qid in query_ids if qid in qrels}
    
    # Connect to Weaviate
    logger.info(f"Connecting to Weaviate at {args.weaviate_url}")
    client = weaviate.Client(args.weaviate_url)
    
    # Test direct retrieval
    start_time = time.time()
    direct_results = direct_weaviate_retrieval(client, queries, args.top_k)
    direct_time = time.time() - start_time
    
    # Test agent-based retrieval if not skipped
    agent_results = {}
    agent_time = 0
    if not args.skip_agent:
        start_time = time.time()
        agent_results = agent_based_retrieval(queries, args.top_k)
        agent_time = time.time() - start_time
    
    # Evaluate results
    direct_metrics = evaluate_results(direct_results, qrels)
    
    # Print results
    print("\n" + "="*50)
    print(f"Retrieval Accuracy Results (top-{args.top_k})")
    print("="*50)
    
    print("\nDirect Weaviate Retrieval:")
    print(f"Time: {direct_time:.2f} seconds ({direct_time/len(queries):.2f} seconds per query)")
    for metric in METRICS:
        print(f"{metric}: {direct_metrics[metric]:.4f}")
    
    # Results dictionary
    results = {
        "direct": {
            "metrics": direct_metrics,
            "time": direct_time,
            "time_per_query": direct_time/len(queries)
        },
        "test_size": len(queries),
        "top_k": args.top_k
    }
    
    # Add agent results if available
    if not args.skip_agent:
        agent_metrics = evaluate_results(agent_results, qrels)
        
        print("\nAgent-based Retrieval:")
        print(f"Time: {agent_time:.2f} seconds ({agent_time/len(queries):.2f} seconds per query)")
        for metric in METRICS:
            print(f"{metric}: {agent_metrics[metric]:.4f}")
        
        print("\nImprovement:")
        for metric in METRICS:
            improvement = agent_metrics[metric] - direct_metrics[metric]
            print(f"{metric}: {improvement:.4f} ({improvement/direct_metrics[metric]*100:.2f}%)")
        
        # Add agent results to the dictionary
        results["agent"] = {
            "metrics": agent_metrics,
            "time": agent_time,
            "time_per_query": agent_time/len(queries)
        }
    
    results_path = os.path.join(args.data_path, "retrieval_results.json")
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {results_path}")

if __name__ == "__main__":
    main()
