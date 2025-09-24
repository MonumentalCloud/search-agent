#!/usr/bin/env python3
"""
Run the search agent with logging to a file.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path

# Create logs directory if it doesn't exist
logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Configure logging
log_file = logs_dir / "search_agent.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Starting search agent with logging to {log_file}")

# Run the actual script with the same arguments
run_script = Path(__file__).parent / "run.py"
args = sys.argv[1:]

logger.info(f"Running {run_script} with args: {args}")

# Execute the run.py script with the same arguments
try:
    result = subprocess.run(
        [sys.executable, str(run_script)] + args,
        check=True,
        text=True,
        capture_output=True
    )
    logger.info(f"Command output:\n{result.stdout}")
    if result.stderr:
        logger.warning(f"Command stderr:\n{result.stderr}")
    sys.exit(result.returncode)
except subprocess.CalledProcessError as e:
    logger.error(f"Command failed with exit code {e.returncode}")
    logger.error(f"Command output:\n{e.stdout}")
    logger.error(f"Command stderr:\n{e.stderr}")
    sys.exit(e.returncode)
except Exception as e:
    logger.exception(f"Failed to run command: {e}")
    sys.exit(1)
