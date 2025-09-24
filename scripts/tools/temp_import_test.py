import sys
from pathlib import Path
import os

print(f"DEBUG: Current working directory: {os.getcwd()}")

# Assuming this script is run from project root (/Users/jinjae/search_agent)
project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

utils_path = project_root / "utils"
sys.path.insert(0, str(utils_path))

print(f"DEBUG: sys.path after modifications: {sys.path}")
print(f"DEBUG: Checking if utils_path exists: {utils_path.exists()}")
print(f"DEBUG: Checking if utils_path is a directory: {utils_path.is_dir()}")
print(f"DEBUG: Contents of utils_path: {list(utils_path.iterdir()) if utils_path.is_dir() else 'N/A'}")

try:
    from utils.pid_manager import PIDManager
    print("DEBUG: Successfully imported PIDManager from utils.")
except ModuleNotFoundError as e:
    print(f"DEBUG: ModuleNotFoundError on PIDManager: {e}")
except Exception as e:
    print(f"DEBUG: Unexpected error on PIDManager import: {e}")


