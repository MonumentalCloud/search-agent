#!/usr/bin/env python3
"""
Fix the graph.py file to use ChromaDB instead of Weaviate.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_graph_imports():
    """
    Fix the imports in graph.py to use ChromaDB instead of Weaviate.
    """
    graph_file = project_root / "agent" / "graph.py"
    
    # Read the current content
    with open(graph_file, "r") as f:
        content = f.read()
    
    # Replace the import for candidate_search with candidate_search_chroma
    content = content.replace(
        "from agent.nodes.candidate_search import first_pass_search as candidate_search",
        "from agent.nodes.candidate_search_chroma import first_pass_search as candidate_search # Use Chroma-based search"
    )
    
    # Write the updated content
    with open(graph_file, "w") as f:
        f.write(content)
    
    print(f"Updated {graph_file} to use ChromaDB instead of Weaviate")

if __name__ == "__main__":
    fix_graph_imports()
