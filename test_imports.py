#!/usr/bin/env python3
"""
Test script to check if all required modules can be imported.
"""

import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Print Python information
logger.info(f"Python executable: {sys.executable}")
logger.info(f"Python version: {sys.version}")
logger.info(f"Python path: {sys.path}")

# Try importing key modules
modules_to_test = [
    "chromadb",
    "fastapi",
    "uvicorn",
    "pydantic",
    "numpy",
    "langchain",
    "opentelemetry",
]

for module_name in modules_to_test:
    try:
        module = __import__(module_name)
        if hasattr(module, "__version__"):
            logger.info(f"✅ Successfully imported {module_name} (version: {module.__version__})")
        else:
            logger.info(f"✅ Successfully imported {module_name}")
    except ImportError as e:
        logger.error(f"❌ Failed to import {module_name}: {e}")

# Try importing local modules
local_modules = [
    "adapters.chroma_adapter",
    "configs.load",
    "ingestion.metadata_vectors_chroma",
]

for module_name in local_modules:
    try:
        module = __import__(module_name, fromlist=["dummy"])
        logger.info(f"✅ Successfully imported {module_name}")
    except ImportError as e:
        logger.error(f"❌ Failed to import {module_name}: {e}")

logger.info("Import test complete")
