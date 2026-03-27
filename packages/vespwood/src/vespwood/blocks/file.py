from pathlib import Path


class File:
    __slots__ = "_id", "_url", "_filename", "_data"

    _id: str | None
    _url: str | None
    _data: str | bytes | None

    def __init__(self, id: str | None = None, filename: str | None = None, url: str | None = None, local: str | None = None, data: str | bytes | None = None):
        self._id = id
        self._filename = filename
        self._url = url
        self._data = data
        if local:
            self._filename = Path(local).name
            self._data = open(local, "rb").read()