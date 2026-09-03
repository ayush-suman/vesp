from __future__ import annotations

class Image:
    __slots__ = "_id", "_url", "_data"

    _id: str | None
    _url: str | None
    _data: str | bytes | None

    def __init__(self, id: str | None = None, url: str | None = None, local: str | None = None, data: str | bytes | None = None):
        self._id = id
        self._url = url
        self._data = data
        if local:
            self._data = open(local, "rb").read()

    def copy(self) -> Image:
        return Image(id=self._id, url=self._url, data=self._data)