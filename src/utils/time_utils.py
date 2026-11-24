import logging
import time


def format_elapsed(seconds: float) -> str:
  total_ms = round(seconds * 1000)
  hours, rem_ms = divmod(total_ms, 3_600_000)
  minutes, rem_ms = divmod(rem_ms, 60_000)
  secs, ms = divmod(rem_ms, 1000)
  return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"

class ElapsedTimeFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.time()

    def format(self, record):
        elapsed = time.time() - self.start_time
        record.elapsed = format_elapsed(elapsed)
        return super().format(record)
