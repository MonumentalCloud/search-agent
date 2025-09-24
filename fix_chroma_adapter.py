#!/usr/bin/env python3
"""
Fix the ChromaAdapter to use SentenceTransformer for chunk stats.
"""

import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Update the ChromaAdapter to use SentenceTransformer for chunk stats."""
    try:
        project_root = Path(__file__).parent
        adapter_path = project_root / "adapters" / "chroma_adapter.py"
        
        # Read the current file content
        with open(adapter_path, "r") as f:
            content = f.readlines()
        
        # Find the update_chunk_stats method
        in_method = False
        start_line = 0
        end_line = 0
        
        for i, line in enumerate(content):
            if line.strip() == "def update_chunk_stats(self, chunk_id: str, stats: Dict[str, Any]) -> bool:":
                in_method = True
                start_line = i
            elif in_method and line.strip().startswith("def "):
                end_line = i
                break
        
        if end_line == 0:
            end_line = len(content)
        
        # Create the updated method
        updated_method = [
            "    def update_chunk_stats(self, chunk_id: str, stats: Dict[str, Any]) -> bool:\n",
            "        \"\"\"Update chunk stats.\"\"\"\n",
            "        if not self._connected or self._client is None:\n",
            "            logger.warning(\"Not connected to Chroma, skipping chunk stats update\")\n",
            "            return False\n",
            "        \n",
            "        try:\n",
            "            # Get or create the ChunkStats collection\n",
            "            try:\n",
            "                collection = self._client.get_collection(\"ChunkStats\")\n",
            "            except Exception:\n",
            "                # Use SentenceTransformer for consistent embedding dimensions\n",
            "                from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction\n",
            "                embedding_function = SentenceTransformerEmbeddingFunction(model_name=\"all-MiniLM-L6-v2\")\n",
            "                \n",
            "                collection = self._client.create_collection(\n",
            "                    name=\"ChunkStats\",\n",
            "                    embedding_function=embedding_function,\n",
            "                    metadata={\"description\": \"Chunk statistics\"}\n",
            "                )\n",
            "            \n",
            "            # Use SentenceTransformer for embeddings\n",
            "            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction\n",
            "            embeddings = SentenceTransformerEmbeddingFunction(model_name=\"all-MiniLM-L6-v2\")\n",
            "            \n",
            "            # Generate embedding for the chunk ID\n",
            "            embedding = embeddings([chunk_id])[0]\n",
            "            \n",
            "            # Prepare metadata\n",
            "            metadata = {\n",
            "                \"chunk_id\": chunk_id,\n",
            "                \"useful_count\": stats.get(\"useful_count\", 0),\n",
            "                \"last_useful_at\": stats.get(\"last_useful_at\", \"\"),\n",
            "                \"decayed_utility\": stats.get(\"decayed_utility\", 0.0)\n",
            "            }\n",
            "            \n",
            "            # Upsert to collection\n",
            "            collection.upsert(\n",
            "                ids=[chunk_id],\n",
            "                embeddings=[embedding],\n",
            "                metadatas=[metadata],\n",
            "                documents=[chunk_id]  # Use chunk_id as document content\n",
            "            )\n",
            "            \n",
            "            return True\n",
            "            \n",
            "        except Exception as e:\n",
            "            logger.error(f\"Failed to update chunk stats: {e}\")\n",
            "            return False\n",
        ]
        
        # Replace the method in the content
        new_content = content[:start_line] + updated_method + content[end_line:]
        
        # Write the updated content back to the file
        with open(adapter_path, "w") as f:
            f.writelines(new_content)
        
        logger.info("ChromaAdapter updated successfully to use SentenceTransformer")
        return True
    
    except Exception as e:
        logger.error(f"Error updating ChromaAdapter: {e}")
        return False

if __name__ == "__main__":
    main()
