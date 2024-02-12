import math
import numpy
from helpers import interpolate
from link import Link
from link_map import LinkMap
from python_solvespace import SolverSystem
from slvs_writer import SlvsWriter
from type_aliases import Coords, Point, Workplane

class Linkage:
    solver_system: SolverSystem
    slvs_writer: SlvsWriter
    workplane: Workplane
    points: list[Point]
    link_map: LinkMap
    origin: Point

    def __init__(self) -> None:
        self.solver_system = SolverSystem()
        self.slvs_writer = SlvsWriter()
        self.workplane = self.solver_system.create_2d_base()
        self.points = []
        self.link_map = LinkMap()
        self.origin = self.add_pinned_point((0, 0))

    def solve(self) -> int:
        return self.solver_system.solve()

    def write_slvs(self, path: str) -> None:
        self.slvs_writer.write(path)

    def coords(self, point: Point) -> numpy.array:
        return numpy.array(self.solver_system.params(point.params))

    def all_coords(self, *points: list[Point]) -> list[numpy.array]:
        return [self.coords(point) for point in points]

    def set_coords(self, point: Point, coords: Coords) -> None:
        self.solver_system.set_params(point.params, coords)

    def add_point(self, coords: Coords) -> Point:
        x, y = coords
        point = self.solver_system.add_point_2d(x, y, self.workplane)
        self.points.append(point)
        self.slvs_writer.add_point(point, x, y)
        return point

    def add_helper_point(self) -> Point:
        return self.add_point((0, 0))

    def add_pinned_point(self, coords: Coords) -> Point:
        x, y = coords
        point = self.add_point(coords)
        self.pin_point(point)
        if hasattr(self, "origin"):
            self.link_points(self.origin, point).length = math.hypot(x, y)
        return point

    def link_points(self, a: Point, b: Point) -> Link:
        link = self.link_map.link_between(a, b)
        if link:
            return link
        line = self.solver_system.add_line_2d(a, b, self.workplane)
        link = self.link_map.add_link(a, b, line)
        self.slvs_writer.add_line(line, a, b)
        return link

    def link_point_pairs(self, *point_pairs: list[tuple[Point, Point]]) -> list[Link]:
        return [self.link_points(a, b) for a, b in point_pairs]

    def add_point_between(self, a: Point, b: Point, ratio: float) -> Point:
        point = self.add_point(interpolate(self.coords(a), self.coords(b), ratio))
        long_link, short_link = self.link_point_pairs((a, b), (a, point))
        self.coincident(point, long_link)
        self.ratio(short_link, long_link, ratio)
        return point

    def get_length(self, a: Point, b: Point) -> float:
        return self.link_points(a, b).get_length()

    def get_lengths(self, *points: list[Point], to: Point) -> float:
        return [self.get_length(point, to) for point in points]

    def link_points_with_length(self, a: Point, b: Point, length: float) -> Link:
        link = self.link_points(a, b)
        self.length(link, length)
        return link

    ### constraints

    def pin_point(self, point: Point) -> None:
        self.solver_system.dragged(point, self.workplane)
        self.slvs_writer.add_constraint(type = 200, points = [point])

    def length(self, link: Link, length: float) -> None:
        assert not link.has_length(), "already has a length"
        length = math.fabs(length)
        link.length = length
        self.solver_system.distance(link.a, link.b, length, self.workplane)
        self.slvs_writer.add_constraint(type = 30, value = length, points = [link.a, link.b])

    def angle(self, a: Link, b: Link, degrees: float) -> None:
        self.solver_system.angle(a.line, b.line, degrees, self.workplane)
        self.slvs_writer.add_constraint(type = 120, value = degrees, lines = [a.line, b.line])

    def coincident(self, point: Point, link: Link) -> None:
        self.solver_system.coincident(point, link.line, self.workplane)
        self.slvs_writer.add_constraint(type = 42, points = [point], lines = [link.line])

    def assert_proper_length_constraint(self, a: Link, b: Link, unconstrained_ok = False) -> None:
        if unconstrained_ok and not a.has_length() and not b.has_length():
            return
        assert a.has_length() != b.has_length(), "under- or overconstrained equality"

    def equal(self, a: Link, b: Link, *, unconstrained_ok = False) -> None:
        self.assert_proper_length_constraint(a, b, unconstrained_ok)
        if b.has_length():
            a.length = b.length
        if a.has_length():
            b.length = a.length
        self.solver_system.equal(a.line, b.line, self.workplane)
        self.slvs_writer.add_constraint(type = 50, lines = [a.line, b.line])

    def ratio(self, a: Link, b: Link, ratio: float) -> None:
        self.assert_proper_length_constraint(a, b)
        if b.has_length():
            a.length = b.length * ratio
        if a.has_length():
            b.length = a.length / ratio
        self.solver_system.ratio(a.line, b.line, ratio, self.workplane)
        self.slvs_writer.add_constraint(type = 51, value = ratio, lines = [a.line, b.line])

    def parallel(self, a: Link, b: Link) -> None:
        self.solver_system.parallel(a.line, b.line, self.workplane)
        self.slvs_writer.add_constraint(type = 121, lines = [a.line, b.line])

    def horizontal(self, link: Link) -> None:
        self.solver_system.horizontal(link.line, self.workplane)
        self.slvs_writer.add_constraint(type = 80, lines = [link.line])

    def vertical(self, link: Link) -> None:
        self.solver_system.vertical(link.line, self.workplane)
        self.slvs_writer.add_constraint(type = 81, lines = [link.line])
