import logging
from typing import Dict, List

from agent.types import PlannerOutput
from ingestion.metadata_vectors_chroma import get_facet_weights_for_query

logger = logging.getLogger(__name__)


def pick_facet_branches(plan: PlannerOutput, facet_hist: Dict[str, Dict[str, int]], query: str = "") -> List[Dict[str, str]]:
    """Pick facet branches using both planner output and metadata vectors."""
    branches: List[Dict[str, str]] = []
    
    # Start with planner's candidate facet sets
    branches.extend(plan.get("facet_sets", []))
    
    # Get facet weights from metadata vectors if available
    if query:
        try:
            facet_weights = get_facet_weights_for_query(query) # Call the synchronous function
            
            # Add branches based on high-weight facet values
            for facet, weights in facet_weights.items():
                for value, weight in weights.items():
                    if weight > 0.3:  # Threshold for inclusion
                        branches.append({facet: value})
                        logger.debug(f"Added branch from metadata vectors: {facet}={value} (weight: {weight:.3f})")
        except Exception as e:
            logger.warning(f"Could not get facet weights: {e}")
    
    # Fallback: add top histogram modes if no metadata vectors
    if not query or not branches:
        for facet, counts in facet_hist.items():
            if counts:
                top_value = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[0][0]
                branches.append({facet: top_value})
                logger.debug(f"Added branch from histogram: {facet}={top_value}")
    
    # Debug: print branches to see what's causing the issue
    logger.debug(f"Branches before deduplication: {branches}")
    for i, b in enumerate(branches):
        if isinstance(b, dict):
            logger.debug(f"Branch {i}: {b} (types: {[(k, type(v).__name__) for k, v in b.items()]})")
        else:
            logger.debug(f"Branch {i}: {b} (type: {type(b).__name__})")
            # Convert non-dict branches to dicts to avoid errors
            if isinstance(b, list) and len(b) > 0:
                # Try to convert list to dict if it contains key-value pairs
                try:
                    branches[i] = dict(b)
                    logger.info(f"Converted list branch to dict: {branches[i]}")
                except (ValueError, TypeError):
                    # If conversion fails, replace with empty dict
                    branches[i] = {"general": "fallback"}
                    logger.warning(f"Replaced invalid branch with fallback")
            else:
                # Replace with empty dict
                branches[i] = {"general": "fallback"}
                logger.warning(f"Replaced invalid branch with fallback")
    
    # Deduplicate
    unique: List[Dict[str, str]] = []
    seen = set()
    for b in branches:
        try:
            # Convert list values to strings for hashing
            hashable_items = []
            for k, v in b.items():
                if isinstance(v, list):
                    # Convert list to comma-separated string
                    hashable_items.append((k, ",".join(str(item) for item in v)))
                else:
                    hashable_items.append((k, str(v)))
            
            key = tuple(sorted(hashable_items))
            if key not in seen:
                seen.add(key)
                unique.append(b)
        except Exception as e:
            logger.error(f"Error processing branch {b}: {e}")
            # Check if b is a dictionary before trying to call items()
            if isinstance(b, dict):
                logger.error(f"Branch types: {[(k, type(v).__name__, v) for k, v in b.items()]}")
            else:
                logger.error(f"Branch is not a dictionary: {type(b).__name__}, value: {b}")
            # Skip this branch if it causes issues
            continue
    
    # Limit to top 3 branches
    final_branches = unique[:3]
    logger.info(f"Selected {len(final_branches)} facet branches: {final_branches}")
    
    return final_branches