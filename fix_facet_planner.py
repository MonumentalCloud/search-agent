#!/usr/bin/env python3
"""
Fix the facet_planner.py file to use the ChromaDB version of the metadata_vectors.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_facet_planner():
    """
    Fix the facet_planner.py file to use the ChromaDB version of the metadata_vectors.
    """
    facet_planner_file = project_root / "agent" / "nodes" / "facet_planner.py"
    
    # Read the current content
    with open(facet_planner_file, "r") as f:
        content = f.read()
    
    # Replace the import for metadata_vectors with metadata_vectors_chroma
    content = content.replace(
        "from ingestion.metadata_vectors import get_facet_weights_for_query",
        "from ingestion.metadata_vectors_chroma import get_facet_weights_for_query"
    )
    
    # Write the updated content
    with open(facet_planner_file, "w") as f:
        f.write(content)
    
    print(f"Updated {facet_planner_file} to use ChromaDB instead of Weaviate")

if __name__ == "__main__":
    fix_facet_planner()
