from dataclasses import dataclass
from type_aliases import Line, Point
from typing import Optional

@dataclass(eq = False)
class Link:
    a: Point
    b: Point
    line: Line
    # known, fixed length of the line, None if not known
    length: Optional[float] = None

    def __eq__(self, value: object) -> bool:
        return id(self) == id(value)

    def __hash__(self) -> int:
        return id(self)

    def has(self, point: Point) -> bool:
        return self.a == point or self.b == point

    def has_length(self) -> bool:
        return self.length is not None

    def get_length(self) -> float:
        assert self.has_length()
        return self.length
