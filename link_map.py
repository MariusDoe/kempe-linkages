from link import Link
from type_aliases import Line, Point
from typing import Optional

class LinkMap:
    links: list[Link]
    links_map: dict[Point, set[Link]]

    def __init__(self) -> None:
        self.links = []
        self.links_map = {}

    def links_of(self, point: Point) -> set[Link]:
        return self.links_map.setdefault(id(point), set())

    def add_link(self, a: Point, b: Point, line: Line) -> Link:
        link = Link(a, b, line)
        self.links_of(a).add(link)
        self.links_of(b).add(link)
        self.links.append(link)
        return link

    def link_between(self, a: Point, b: Point) -> Optional[Link]:
        for link in self.links_of(a):
            if link.has(b):
                return link
        return None
