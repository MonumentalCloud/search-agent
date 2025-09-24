#!/usr/bin/env python3
"""
Script to update run.py to load environment variables
"""

import os
import sys
from pathlib import Path

def update_run_py():
    """Update run.py to load environment variables."""
    # Get the project root directory
    project_root = Path(__file__).parent.absolute()
    
    # Path to run.py
    run_py_path = project_root / 'run.py'
    
    # Check if run.py exists
    if not run_py_path.exists():
        print(f"Error: run.py not found at {run_py_path}")
        return False
    
    # Read the current content of run.py
    with open(run_py_path, 'r') as f:
        content = f.read()
    
    # Find the position to insert the environment loading code
    # We'll insert it after the imports but before the main code
    import_section_end = content.find("# Add project root")
    if import_section_end == -1:
        import_section_end = content.find("# Configure logging")
    
    if import_section_end == -1:
        print("Error: Could not find a suitable insertion point in run.py")
        return False
    
    # Find the line ending at the insertion point
    line_end = content.find('\n', import_section_end)
    if line_end == -1:
        line_end = len(content)
    
    # Create the environment loading code
    env_code = """
# Import load_environment from load_env.py
try:
    from load_env import load_environment
    # Load environment variables from .env file
    load_environment()
except ImportError:
    print("Warning: load_env.py not found, environment variables will not be loaded")
    pass

"""
    
    # Insert the environment loading code
    new_content = content[:line_end+1] + env_code + content[line_end+1:]
    
    # Create a backup of the original file
    backup_path = run_py_path.with_suffix('.py.bak')
    with open(backup_path, 'w') as f:
        f.write(content)
    print(f"Created backup of run.py at {backup_path}")
    
    # Write the updated content
    with open(run_py_path, 'w') as f:
        f.write(new_content)
    
    print(f"Updated run.py to load environment variables")
    return True

if __name__ == "__main__":
    if update_run_py():
        print("Successfully updated run.py")
    else:
        print("Failed to update run.py")
        sys.exit(1)
