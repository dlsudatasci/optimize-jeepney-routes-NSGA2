import logging, time

def format_elapsed(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"

class ElapsedTimeFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = time.time()

    def format(self, record):
        elapsed = time.time() - self.start_time
        record.elapsed = format_elapsed(elapsed)
        return super().format(record)
