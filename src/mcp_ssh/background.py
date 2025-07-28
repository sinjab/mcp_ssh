import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BackgroundProcess:
    """Track a background SSH process."""

    process_id: str
    host: str
    command: str
    pid: int | None
    start_time: datetime
    status: str  # 'running', 'completed', 'failed'
    output_file: str
    error_file: str
    exit_code: int | None = None


class BackgroundProcessManager:
    """Simple process tracking."""

    def __init__(self) -> None:
        self.processes: dict[str, BackgroundProcess] = {}

    def start_process(self, host: str, command: str) -> str:
        """Start tracking a new process."""
        process_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Use system temp directory for better security
        temp_dir = os.environ.get("MCP_SSH_TEMP_DIR", tempfile.gettempdir())

        process = BackgroundProcess(
            process_id=process_id,
            host=host,
            command=command,
            pid=None,
            start_time=datetime.now(),
            status="running",
            output_file=f"{temp_dir}/mcp_ssh_{process_id}_{timestamp}.out",
            error_file=f"{temp_dir}/mcp_ssh_{process_id}_{timestamp}.err",
        )

        self.processes[process_id] = process
        return process_id

    def get_process(self, process_id: str) -> BackgroundProcess | None:
        """Get process by ID."""
        return self.processes.get(process_id)

    def update_process(
        self,
        process_id: str,
        pid: int | None = None,
        status: str | None = None,
        exit_code: int | None = None,
    ) -> None:
        """Update process info."""
        if process_id in self.processes:
            if pid is not None:
                self.processes[process_id].pid = pid
            if status is not None:
                self.processes[process_id].status = status
            if exit_code is not None:
                self.processes[process_id].exit_code = exit_code


# Global process manager
process_manager = BackgroundProcessManager()
