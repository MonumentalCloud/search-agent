import json
import logging
import os
from typing import Dict, List, Optional
from langchain.tools import tool
from langchain_core.language_models import BaseLanguageModel

from configs.load import get_default_llm
from agent.types import RerankedChunk, Answer

logger = logging.getLogger(__name__)


@tool
def extract_citations(chunk_id: str, text: str) -> str:
    """Extract citations from a chunk of text."""
    # Placeholder implementation
    return f"Citations from chunk {chunk_id}"


def compose_answer(query: str, top: List[RerankedChunk], llm: Optional[BaseLanguageModel] = None) -> Answer:
    """Compose final answer using LLM and prompt."""
    logger.info(f"Composing answer for query: {query} with {len(top)} results")
    
    # Use LLM for answer generation if we have results
    if len(top) > 0:
        # Get the LLM
        llm = llm or get_default_llm()
        
        # Load the answerer prompt
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "..", "configs", "prompts", "answerer.txt")
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        # Prepare the chunks for the prompt
        chunks_text = ""
        for i, chunk in enumerate(top[:5]):  # Use top 5 chunks
            chunks_text += f"\nCHUNK {i+1}:\n"
            chunks_text += f"ID: {chunk.get('chunk_id', 'unknown')}\n"
            chunks_text += f"Document: {chunk.get('doc_id', 'unknown')}\n"
            chunks_text += f"Section: {chunk.get('section', 'unknown')}\n"
            if chunk.get('valid_from'):
                chunks_text += f"Date: {chunk.get('valid_from')}\n"
            if chunk.get('author'):
                chunks_text += f"Author: {chunk.get('author')}\n"
            chunks_text += f"Content: {chunk.get('body', '')}\n"
        
        # Create the full prompt
        full_prompt = f"{prompt_template}\n\nUser Query: {query}\n\nAvailable Chunks:\n{chunks_text}"
        
        try:
            # Get response from LLM
            response = llm.invoke(full_prompt)
            
            # Extract content from response
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            # Try to parse JSON from response
            try:
                # Clean up the content to extract JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                result = json.loads(content.strip())
                
                # Ensure the result has the expected structure
                if not isinstance(result, dict) or "text" not in result or "citations" not in result:
                    raise ValueError("LLM response does not have the expected structure")
                
                # Add citations if they're not already in the right format
                if not result["citations"] or not isinstance(result["citations"][0], dict):
                    result["citations"] = [
                        {
                            "doc_id": chunk.get('doc_id', 'unknown'),
                            "chunk_id": chunk.get('chunk_id', 'unknown'),
                            "section": chunk.get('section', 'unknown'),
                            "valid_from": chunk.get('valid_from'),
                            "valid_to": chunk.get('valid_to'),
                            "body": chunk.get('body', '')
                        }
                        for chunk in top[:3]
                    ]
            except Exception as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                # Fallback to using the response as the answer text
                result = {
                    "text": content.strip(),
                    "citations": [
                        {
                            "doc_id": chunk.get('doc_id', 'unknown'),
                            "chunk_id": chunk.get('chunk_id', 'unknown'),
                            "section": chunk.get('section', 'unknown'),
                            "valid_from": chunk.get('valid_from'),
                            "valid_to": chunk.get('valid_to'),
                            "body": chunk.get('body', '')
                        }
                        for chunk in top[:3]
                    ]
                }
        except Exception as e:
            logger.error(f"Error generating answer with LLM: {e}")
            # Fallback to simple answer
            result = {
                "text": f"Based on the search results, I found information related to your query. However, I couldn't generate a proper response due to a technical issue.",
                "citations": [
                    {
                        "doc_id": chunk.get('doc_id', 'unknown'),
                        "chunk_id": chunk.get('chunk_id', 'unknown'),
                        "section": chunk.get('section', 'unknown'),
                        "valid_from": chunk.get('valid_from'),
                        "valid_to": chunk.get('valid_to'),
                        "body": chunk.get('body', '')
                    }
                    for chunk in top[:3]
                ]
            }
    else:
        result = {
            "text": f"I couldn't find specific information about '{query}' in the available documents. Please try rephrasing your question or check if the relevant documents are available.",
            "citations": []
        }
    
    logger.info(f"Answerer result: {result}")
    return result
