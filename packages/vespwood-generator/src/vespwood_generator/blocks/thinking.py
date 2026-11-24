from __future__ import annotations

class Thinking:
    def __init__(self, signature: str, id: str | None = None, summary: list[str] | str = []):
        self._id = id
        self._summary = summary if isinstance(summary, list) else [summary]
        self._signature = signature

    @property
    def id(self) -> str | None:
        return self._id

    @property
    def summary(self) -> list[str]:
        return self._summary

    @property
    def signature(self) -> str:
        return self._signature

    def copy(self) -> Thinking:
        return Thinking(self._signature, self._id, self._summary)

    @property
    def json(self):
        return {"id": self.id, "summary": self.summary, "signature": self.signature }