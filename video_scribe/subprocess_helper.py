import queue
import subprocess
import threading
from typing import Optional, Tuple

class StreamReader:
    """Generic subprocess output stream reader."""

    def __init__(self, process: subprocess.Popen):
        self.process = process
        self.output_queue = queue.Queue()
        self.threads = []

    def start_reading(self) -> None:
        if self.process.stdout:
            stdout_thread = threading.Thread(
                target=self._read_stream, args=(self.process.stdout, "stdout"), daemon=True
            )
            stdout_thread.start()
            self.threads.append(stdout_thread)

        if self.process.stderr:
            stderr_thread = threading.Thread(
                target=self._read_stream, args=(self.process.stderr, "stderr"), daemon=True
            )
            stderr_thread.start()
            self.threads.append(stderr_thread)

    def _read_stream(self, stream, stream_name: str) -> None:
        try:
            for line in iter(stream.readline, ""):
                if line:
                    self.output_queue.put((stream_name, line))
        except Exception:
            pass
        finally:
            stream.close()

    def get_output(self, timeout: float = 0.1) -> Optional[Tuple[str, str]]:
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_remaining_output(self) -> list:
        output = []
        while not self.output_queue.empty():
            try:
                output.append(self.output_queue.get_nowait())
            except queue.Empty:
                break
        return output
