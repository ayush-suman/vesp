from __future__ import annotations

class Tag(str):
    def indexed(self, *indices: int) -> Tag:
        indices = map(lambda idx: str(idx), indices)
        joined_indices = "#".join(indices)
        return Tag(f"{self}#{joined_indices}")
    
    @property
    def has_index(self) -> bool:
        return "#" in self

    @property
    def base(self) -> Tag:
        return Tag(self.rsplit("#", 1)[0])

    @property
    def index(self) -> int | None:
        parts = self.rsplit("#", 1)
        if len(parts) == 2:
            return int(parts[1])
        else:
            return None
    
    
