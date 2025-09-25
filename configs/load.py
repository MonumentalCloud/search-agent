"""
Configuration loading utilities.
"""

import os
import logging
import yaml
from typing import Any, Dict, Optional, Union, List
from pathlib import Path
import re

logger = logging.getLogger(__name__)

# Set up root logger for the application
def setup_root_logger(level: str = "INFO"):
    """Set up the root logger for the application."""
    import logging
    from logging import StreamHandler
    from logging.handlers import RotatingFileHandler
    import sys
    
    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Create console handler
    console = StreamHandler(sys.stdout)
    console.setLevel(numeric_level)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console)
    
    # Create file handler
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    return root_logger

def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """
    Load YAML configuration file.
    
    Args:
        config_path: Path to the YAML configuration file.
        
    Returns:
        Dict containing the configuration.
    """
    try:
        logger.debug(f"Loading {os.path.basename(config_path)} from: {config_path}")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Process environment variable placeholders
        config = _expand_env_vars(config)
        return config
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        return {}

def _expand_env_vars(config: Any) -> Any:
    """
    Recursively expand environment variables in the configuration.
    
    Args:
        config: Configuration object (dict, list, or scalar).
        
    Returns:
        Configuration with environment variables expanded.
    """
    if isinstance(config, dict):
        return {k: _expand_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_expand_env_vars(v) for v in config]
    elif isinstance(config, str):
        # Replace ${VAR} or $VAR with the environment variable
        pattern = r'\${([^}]+)}|\$([A-Za-z0-9_]+)'
        
        def replace_var(match):
            var_name = match.group(1) or match.group(2)
            return os.environ.get(var_name, match.group(0))
        
        return re.sub(pattern, replace_var, config)
    else:
        return config

def get_default_config() -> Dict[str, Any]:
    """
    Get the default configuration.
    
    Returns:
        Dict containing the default configuration.
    """
    config_dir = os.path.dirname(os.path.abspath(__file__))
    default_config_path = os.path.join(config_dir, "default.yaml")
    return load_yaml_config(default_config_path)

def get_default_llm(model: Optional[str] = None):
    """
    Get the default language model.
    
    Args:
        model: Optional model name to override the default.
        
    Returns:
        Language model instance.
    """
    cfg = get_default_config()
    llm_cfg = cfg.get("llm", {})
    
    if model:
        llm_cfg["model"] = model
    
    provider = llm_cfg.get("provider", "openai")
    logger.debug(f"in get_default_llm: llm_cfg = {llm_cfg}")
    logger.debug(f"in get_default_llm: provider = '{provider}' (type: {type(provider)}) ")
    
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=llm_cfg.get("model", "gpt-4o"),
            temperature=float(llm_cfg.get("temperature", 0.0)),
            api_key=llm_cfg.get("api_key"),
            base_url=llm_cfg.get("base_url")
        )
    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI
        
        # Get the API key from config
        api_key = llm_cfg.get("api_key")
        if not api_key:
            raise ValueError("OpenRouter API key not found in configuration")
        
        # Set the environment variable as a fallback for LangChain
        os.environ["OPENAI_API_KEY"] = api_key
        
        return ChatOpenAI(
            model=llm_cfg.get("model", "openai/gpt-4o-mini"),
            temperature=float(llm_cfg.get("temperature", 0.0)),
            api_key=api_key,
            base_url=llm_cfg.get("base_url", "https://openrouter.ai/api/v1")
        )
    elif provider == "huggingface":
        from langchain_huggingface import ChatHuggingFace
        return ChatHuggingFace(
            model_id=llm_cfg.get("model", "mistralai/Mixtral-8x7B-Instruct-v0.1"),
            temperature=float(llm_cfg.get("temperature", 0.0)),
            token=llm_cfg.get("api_key")
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

def get_default_embeddings():
    """
    Get the default embeddings model.
    
    Returns:
        Embeddings model instance.
    """
    cfg = get_default_config()
    emb_cfg = cfg.get("embeddings", {})
    
    provider = emb_cfg.get("provider", "openai")
    logger.debug(f"in get_default_embeddings: emb_cfg = {emb_cfg}")
    logger.debug(f"in get_default_embeddings: provider = '{provider}' (type: {type(provider)}) ")
    
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=emb_cfg.get("model", "text-embedding-3-small"),
            api_key=emb_cfg.get("api_key")
        )
    elif provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name=emb_cfg.get("model", "BAAI/bge-small-en-v1.5"),
            encode_kwargs={"normalize_embeddings": True}
        )
    elif provider == "requests":
        # Custom implementation for API-based embeddings
        from langchain.embeddings.base import Embeddings
        
        class RequestBasedEmbeddings(Embeddings):
            def __init__(self, api_key: str, base_url: str, model: str, dimensions: int = 1024):
                self.api_key = api_key
                self.base_url = base_url
                self.model = model
                self.dimensions = dimensions
            
            def embed_documents(self, texts: List[str]) -> List[List[float]]:
                """Embed a list of documents."""
                return [self.embed_query(text) for text in texts]
            
            def embed_query(self, text: str) -> List[float]:
                """Embed a query."""
                import requests
                import numpy as np
                
                # Log the API call (without the full text for privacy)
                logger.debug(f"RequestBasedEmbeddings - Calling API: {self.base_url}")
                logger.debug(f"RequestBasedEmbeddings - API Key (first 5 chars): {self.api_key[:5] if self.api_key and len(self.api_key) > 5 else self.api_key}...")
                logger.debug(f"RequestBasedEmbeddings - Model: {self.model}")
                logger.debug(f"RequestBasedEmbeddings - Input texts (first): {text[:20]}...")
                
                try:
                    response = requests.post(
                        f"{self.base_url}/embeddings",
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {self.api_key}"
                        },
                        json={
                            "model": self.model,
                            "input": text
                        }
                    )
                    
                    response.raise_for_status()
                    embedding_data = response.json()
                    
                    # Extract the embedding from the response
                    if "data" in embedding_data and len(embedding_data["data"]) > 0:
                        embedding = embedding_data["data"][0]["embedding"]
                        return embedding
                    else:
                        # If the API doesn't return an embedding, return a zero vector
                        logger.error(f"API did not return embedding data: {embedding_data}")
                        return [0.0] * self.dimensions
                        
                except Exception as e:
                    # If the API call fails, return a zero vector
                    logger.error(f"Error calling embedding API: {e}")
                    # Return a random vector instead of zeros to avoid clustering
                    return list(np.random.normal(0, 0.1, self.dimensions))
        
        return RequestBasedEmbeddings(
            api_key=emb_cfg.get("api_key"),
            base_url=emb_cfg.get("base_url"),
            model=emb_cfg.get("model", "bge-m3"),
            dimensions=int(emb_cfg.get("dimensions", 1024))
        )
    else:
        raise ValueError(f"Unsupported embeddings provider: {provider}")