import sys
import asyncio
from pathlib import Path
import os # Import os for getcwd

# Get project root from current working directory
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "configs"))

from configs.load import get_default_llm


