import json
import logger

class TaskLog:
    def __init__(self, filename, dup2log=True):
        self.filename = filename
        self.messages = []
        self.progress = 0.0
        self.progress_max = 100.0
        self.dup2log = dup2log

    def info(self, msg, progress=None):
        self.log(msg, progress)

    def log(self, msg, progress=None):
        if progress is not None:
            self.progress = progress
        self.messages.append(msg)

        if self.dup2log:
            logger.info(msg)

        r = {
            "progress": round(self.progress),
            "progress_max": round(self.progress_max),
            "progress_percent": round(self.progress / self.progress_max * 100.0),
            "messages": self.messages
        }
        with open(self.filename, "w") as f:
            json.dump(r, f)