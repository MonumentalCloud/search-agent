import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional
import subprocess

logger = logging.getLogger(__name__)

class PIDManager:
    """Manages PIDs of background services."""
    def __init__(self, pid_file_path: Optional[Path] = None):
        self.pid_file = pid_file_path if pid_file_path else (Path.cwd() / ".agent_pids")
        self._ensure_dir(self.pid_file.parent)

    def _ensure_dir(self, path: Path):
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

    def _read_pids(self) -> Dict[str, int]:
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Corrupt PID file {self.pid_file}, clearing.")
                self.pid_file.unlink(missing_ok=True)
                return {}
        return {}

    def _write_pids(self, pids: Dict[str, int]):
        with open(self.pid_file, 'w') as f:
            json.dump(pids, f, indent=2)

    def store_pid(self, service_name: str, pid: int):
        pids = self._read_pids()
        pids[service_name] = pid
        self._write_pids(pids)
        logger.info(f"Stored PID for {service_name}: {pid} in {self.pid_file}")

    def get_pid(self, service_name: str) -> Optional[int]:
        pids = self._read_pids()
        return pids.get(service_name)

    def remove_pid(self, service_name: str):
        pids = self._read_pids()
        if service_name in pids:
            del pids[service_name]
            self._write_pids(pids)
            logger.info(f"Removed PID for {service_name} from {self.pid_file}")

    def clear_all_pids(self):
        self._write_pids({})
        logger.info(f"Cleared all PIDs in {self.pid_file}")

    def terminate_all_processes(self):
        logger.info(f"Attempting to stop all processes managed by {self.pid_file}...")
        pids = self._read_pids()
        if not pids:
            logger.info(f"No background processes found to stop in {self.pid_file}.")
        
        for service_name, pid in pids.items():
            try:
                os.kill(pid, 0) # Signal 0 does not kill, but checks if PID exists
                os.kill(pid, 9) # SIGKILL
                logger.info(f"Killed {service_name} (PID: {pid})")
            except ProcessLookupError:
                logger.info(f"{service_name} (PID: {pid}) not found or already dead.")
            except Exception as e:
                logger.error(f"Error killing {service_name} (PID: {pid}): {e}", exc_info=True)
        
        self.clear_all_pids()
        logger.info("All managed background processes termination attempt completed.")

    def force_kill_streamlit(self):
        """Forcefully kills any lingering Streamlit processes."""
        try:
            subprocess.run(["pkill", "-f", "streamlit run"], check=False, capture_output=True)
            logger.info("Attempted to forcefully terminate all 'streamlit run' processes.")
        except Exception as e:
            logger.warning(f"Error attempting to pkill streamlit: {e}", exc_info=True)


# Global instance for convenience, can be overridden by start.py if needed
pid_manager = PIDManager()


