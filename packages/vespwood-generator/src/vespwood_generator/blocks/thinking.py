from __future__ import annotations

class Thinking:
    def __init__(self, id: str, summary: list[str], signature: str):
        self._id = id
        self._summary = summary
        self._signature = signature

    @property
    def id(self) -> str:
        return self._id

    @property
    def summary(self) -> list[str]:
        return self._summary

    @property
    def signature(self) -> str:
        return self._signature

    def copy(self) -> Thinking:
        return Thinking(self._id, self._summary, self._signature)

    @property
    def json(self):
        return {"id": self.id, "summary": self.summary, "signature": self.signature }