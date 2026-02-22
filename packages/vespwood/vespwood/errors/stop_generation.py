from src.spider.response import Response


class StopGeneration(Exception):
    def __init__(self, reason: str, response: Response | None = None):
        self.reason = reason
        self.response = response
        super().__init__(reason)