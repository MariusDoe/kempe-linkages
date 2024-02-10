import sympy
from sympy.simplify.fu import TR5, TR8, TR0
from pyslvs import VPoint, t_config, expr_solving
import matplotlib.pyplot as plt
from itertools import pairwise
import numpy
import math

def interpolate(a, b, t: float):
    return a * (1 - t) + b * t

def coords(point: VPoint) -> numpy.array:
    return numpy.array([point.x, point.y])

def normalize(array: numpy.array) -> numpy.array:
    return array / numpy.linalg.norm(array)

def angle_to_x_axis(point: numpy.array) -> float:
    angle = math.atan2(point[1], point[0])
    if angle < 0:
        angle += math.tau
    return angle

def point_from_angle_to_x_axis(angle: float) -> numpy.array:
    return numpy.array([math.cos(angle), math.sin(angle)])

class UnionFind:
    parents: dict

    def __init__(self) -> None:
        self.parents = {}

    def find(self, element):
        if element in self.parents:
            parent = self.find(self.parents[element])
            self.parents[element] = parent
            return parent
        else:
            return element

    def union(self, x, y):
        x_parent = self.find(x)
        y_parent = self.find(y)
        if x_parent == y_parent:
            return
        self.parents[y_parent] = x_parent

def intersection_count(a, b):
    def to_set(x):
        return set(map(id, x))
    return len(to_set(a).intersection(to_set(b)))

class Linkage:
    GROUND = "ground"
    points: list[VPoint]
    next_link_index: int

    def __init__(self):
        self.points = []
        self.next_link_index = 0

    def expr(self):
        point_exprs = ",".join((point.expr() for point in self.points))
        return f"M[{point_exprs}]"

    def index(self, point: VPoint):
        return self.points.index(point)

    def create_input(self, a: VPoint, base: VPoint):
        return (self.index(a), self.index(base))

    def add_point(self, coords: [float, float]) -> VPoint:
        links = ()
        join_type = 0
        angle = 0
        color = "green"
        point = VPoint(links, join_type, angle, color, coords[0], coords[1])
        self.points.append(point)
        return point

    def add_point_between(self, a: VPoint, b: VPoint, t: float) -> VPoint:
        point = self.add_point(interpolate(coords(a), coords(b), t))
        self.link_points(point, a, b)
        return point

    def add_link(self, link_name: str, *points: list[VPoint]):
        for point in points:
            point.set_links(tuple(set([link_name, *point.links])))

    def rename_links(self, rename):
        for point in self.points:
            point.set_links(tuple(set((self.GROUND if link == self.GROUND else rename(link) for link in point.links))))

    def clean_up_links(self) -> str:
        points_for_links = {}
        for point in self.points:
            for link in point.links:
                if link == self.GROUND:
                    continue
                if link not in points_for_links:
                    points_for_links[link] = []
                points_for_links[link].append(point)
        union_find = UnionFind()
        for link, link_points in points_for_links.items():
            other_links = set((
                other_link for point in link_points for other_link in point.links
                if other_link != link and other_link != self.GROUND))
            for other_link in other_links:
                other_link_points = points_for_links[other_link]
                if intersection_count(link_points, other_link_points) >= 2:
                    union_find.union(link, other_link)
        self.rename_links(lambda link: union_find.find(link))

    def remove_link(self, link_name: str, *points: list[VPoint]):
        for point in points:
            point.set_links(tuple(set(point.links) - set([link_name])))

    def next_link(self) -> str:
        link = "L" + str(self.next_link_index)
        self.next_link_index += 1
        return link

    def compress_links(self):
        self.next_link_index = 0
        renames = {self.GROUND: self.GROUND}
        for point in self.points:
            for link in point.links:
                if link in renames:
                    continue
                renames[link] = self.next_link()
        self.rename_links(lambda link: renames[link])

    def are_linked(self, points: list[VPoint], without: list[str] = []) -> bool:
        all_links = [set(point.links) for point in points]
        intersection = all_links[0]
        for links in all_links[1:]:
            intersection = intersection.intersection(links)
        return len(intersection - set(without)) > 0

    def link_points(self, *points: list[VPoint]):
        if self.are_linked(points):
            return
        self.add_link(self.next_link(), *points)

    def link_point_sets(self, *point_sets: list[list[VPoint]]):
        for points in point_sets:
            self.link_points(*points)

    def pin_point(self, point: VPoint):
        self.add_link(self.GROUND, point)

    def add_pinned_point(self, *args, **kwargs):
        point = self.add_point(*args, **kwargs)
        self.pin_point(point)
        return point

class KempeLinkage(Linkage):
    radius: float
    origin: VPoint
    x_axis: VPoint
    source: VPoint

    def __init__(self, radius):
        super().__init__()
        self.radius = radius
        self.origin = self.add_pinned_point((0, 0))
        self.x_axis = self.add_pinned_point((self.radius, 0))

        self.alpha, self.beta = sympy.symbols("a b")
        x = math.sqrt(3) / 2 * self.radius
        self.a = self.add_point((2 * x, x))
        self.b = self.add_point((x, 2 * x))
        self.pen = self.paralellogram(self.origin, self.a, self.b)

    def paralellogram(self, base: VPoint, a: VPoint, b: VPoint) -> VPoint:
        tip = self.add_point(coords(a) + coords(b) - coords(base))
        self.link_point_sets((base, a), (base, b), (a, tip), (b, tip))
        # brace
        # mid_base_a = self.add_point_between(base, a, 0.5)
        # mid_b_tip = self.add_point_between(b, tip, 0.5)
        # self.link_points(mid_base_a, mid_b_tip)
        return tip

    def contra_paralellelogram(self, a: VPoint, b: VPoint, c: VPoint) -> VPoint:
        ab = coords(b) - coords(a)
        ac_norm = normalize(coords(c) - coords(a))
        ab_on_ac = numpy.dot(ab, ac_norm) * ac_norm
        d = self.add_point(coords(c) + ab - 2 * ab_on_ac)
        self.link_point_sets(*pairwise([a, b, c, d, a]))
        # TODO: bracing
        return d

    def multiply_angle(self, input: VPoint, base: VPoint, axis: VPoint, factor: int):
        d = self.contra_paralellelogram(input, base, axis)
        ratio = input.distance(base) / input.distance(d)
        current_input = input
        for _ in range(factor - 1):
            hinge = self.add_point_between(current_input, d, ratio ** 2)
            current_input = self.contra_paralellelogram(hinge, current_input, base)
            d = hinge
        return current_input

    def add_angles(self, a: VPoint, b: VPoint, base: VPoint, axis: VPoint) -> VPoint:
        a_distance = a.distance(base)
        b_distance = b.distance(base)
        ratio = a_distance / b_distance
        base_coords = coords(base)
        def direction(x: VPoint):
            return normalize(coords(x) - base_coords)
        a_direction = direction(a)
        b_direction = direction(b)
        half_sum_direction = point_from_angle_to_x_axis(interpolate(angle_to_x_axis(a_direction), angle_to_x_axis(b_direction), 0.5))
        half_sum_distance = a_distance * ratio ** -0.5
        half_sum = self.add_point(base_coords + half_sum_direction * half_sum_distance)
        hinge = self.contra_paralellelogram(b, base, half_sum)
        d = self.contra_paralellelogram(half_sum, base, a)
        self.link_points(half_sum, hinge, d)
        return self.multiply_angle(half_sum, base, axis, 2)

    def subtract_angles(self, a: VPoint, b: VPoint, base: VPoint, axis: VPoint) -> VPoint:
        a_distance = a.distance(base)
        b_distance = b.distance(base)
        axis_distance = axis.distance(base)
        base_coords = coords(base)
        half_a_direction = point_from_angle_to_x_axis(interpolate(angle_to_x_axis(a), angle_to_x_axis(axis), 0.5))
        half_a_distance = (a_distance * axis_distance) ** 0.5
        half_a = self.add_point(base_coords + half_a_direction * half_a_distance)
        counter_a_half_a = self.contra_paralellelogram(a, base, half_a)
        counter_half_a_axis = self.contra_paralellelogram(half_a, base, axis)
        self.link_points(half_a, counter_a_half_a, counter_half_a_axis)
        difference_direction = point_from_angle_to_x_axis(angle_to_x_axis(a) - angle_to_x_axis(b) + angle_to_x_axis(axis))
        difference_distance = a_distance * axis_distance / b_distance
        difference = self.add_point(base_coords + difference_direction * difference_distance)
        counter_b_half_a = self.contra_paralellelogram(b, base, half_a)
        counter_half_a_difference = self.contra_paralellelogram(half_a, base, difference)
        self.link_points(half_a, counter_b_half_a, counter_half_a_difference)
        return difference

    def add_constant_angle(self, a: VPoint, angle: float, base: VPoint) -> VPoint:
        base_a = coords(a) - coords(base)
        direction = point_from_angle_to_x_axis(angle_to_x_axis(base_a) + angle)
        length = a.distance(base)
        point = self.add_point(coords(base) + length * direction)
        self.link_points(point, a, base)
        return point

    def sum_angles(self, angle, base: VPoint, axis: VPoint) -> VPoint:
        assert angle.is_Add
        def should_sort_to_back(x):
            return x.is_constant() or x.could_extract_minus_sign()
        angles = sorted(angle.args, key = should_sort_to_back)
        vector = self.angle_to_vector(angles[0])
        for angle in angles[1:]:
            if angle.is_constant():
                vector = self.add_constant_angle(vector, angle, base)
            elif angle.could_extract_minus_sign():
                vector = self.subtract_angles(vector, self.angle_to_vector(-angle), base, axis)
            else:
                vector = self.add_angles(vector, self.angle_to_vector(angle), base, axis)
        return vector

    def with_length(self, a: VPoint, length: float, base: VPoint) -> VPoint:
        base_coords = coords(base)
        point = self.add_point(base_coords + length * normalize(coords(a) - base_coords))
        self.link_points(point, a, base)
        return point

    def vector_sum(self, base: VPoint, *vectors: list[VPoint]) -> VPoint:
        while len(vectors) > 0:
            new_base, *translatees = vectors
            vectors = [self.paralellogram(base, new_base, vector) for vector in translatees]
            base = new_base
        return base

    def to_kempe_expression(self, expression, x, y):
        r = sympy.symbols("r")
        x_substitution = (r / 2) * sympy.cos(self.alpha) + (r / 2) * sympy.cos(self.beta)
        y_substitution = (r / 2) * sympy.sin(self.alpha) + (r / 2) * sympy.sin(self.beta)
        substituted = expression.subs(x, x_substitution).subs(y, y_substitution)
        return TR0(TR5(TR8(TR0(substituted)))).rewrite(sympy.cos).subs(r, self.radius)

    def angle_to_vector(self, angle):
        if angle == self.alpha:
            return self.a
        if angle == self.beta:
            return self.b
        if angle.is_Add:
            return self.sum_angles(angle, self.origin, self.x_axis)
        if angle.is_Mul:
            factor, angle = angle.as_coeff_Mul()
            assert factor > 0 and factor % 1 == 0, "invalid cosine angle factor " + str(factor)
            assert not angle.is_Mul, "invalid angle product " + str(angle) # prevents infinite recursion
            return self.multiply_angle(self.angle_to_vector(angle), self.origin, self.x_axis, factor)
        assert False, "unknown angle type"

    def constrain_to_y_axis(self, point: VPoint):
        point_coords = coords(point)
        left_coords = point_coords - (self.radius, 0)
        left = self.add_pinned_point(left_coords)
        mid_coords = interpolate(left_coords, point_coords, 0.5)
        mid = self.add_point(mid_coords)
        circle_center = self.add_pinned_point(interpolate(left_coords, mid_coords, 0.5))
        rhombus_center = interpolate(mid_coords, point_coords, 0.5)
        rhombus_offset = (0, self.radius)
        top = self.add_point(rhombus_center + rhombus_offset)
        bottom = self.add_point(rhombus_center - rhombus_offset)
        self.link_point_sets(
            (circle_center, mid),
            (left, top), (left, bottom),
            (mid, top), (top, point), (point, bottom), (bottom, mid))

    def from_curve(self, expression, x, y):
        expression = self.to_kempe_expression(expression, x, y)
        vectors = []
        constant_offset, scaled_cosines = expression.as_coeff_add(sympy.cos)
        if constant_offset != 0:
            vectors.append(self.add_point((constant_offset, 0)))
        for scaled_cosine in scaled_cosines:
            factor, (cosine,) = scaled_cosine.as_coeff_mul(sympy.cos)
            angle = cosine.args[0]
            vectors.append(self.with_length(self.angle_to_vector(angle), factor, self.origin))
        lock_onto_y_axis = self.vector_sum(self.origin, *vectors)
        self.constrain_to_y_axis(lock_onto_y_axis)

def main():
    linkage = KempeLinkage(20)
    x, y = sympy.symbols("x y")
    # linkage.from_curve(x ** 3 * y - 5 * y ** 2, x, y)
    a = 1 / (2 * math.sqrt(2))
    linkage.from_curve(5 * x - y, x, y)
    linkage.clean_up_links()
    linkage.compress_links()
    print(linkage.expr())

    inputs = (linkage.create_input(linkage.a, linkage.origin),)
    exprs = t_config(linkage.points, inputs)
    xs, ys = [], []

    for angle in numpy.arange(0, 100, 0.05):
        print(angle)
        try:
            result = expr_solving(exprs, linkage.points, {pair: angle for pair in inputs})
            x, y = result[linkage.index(linkage.pen)]
            xs.append(x)
            ys.append(y)
        except Exception as e:
            print(angle, e)
            break
    plt.plot(xs, ys)
    plt.show()

if __name__ == "__main__":
    main()
