import math
import numpy
import sympy
from helpers import angle_to_coords, coords_to_angle, coords_to_angles, interpolate, normalize
from itertools import pairwise
from link import Link
from linkage import Linkage
from options import Options, Visibility
from sympy import Expr, Symbol
from sympy.simplify.fu import TR5, TR8, TR0
from type_aliases import Coords, Point

class KempeLinkage(Linkage):
    radius: float
    options: Options
    alpha: Symbol
    beta: Symbol
    x_axis: Point
    a: Point
    b: Point
    pen: Point
    visible_links: list[Link]
    alpha_degrees: float

    def __init__(self, *, radius: float, pen_start: Coords, **options) -> None:
        super().__init__()
        self.radius = radius
        self.options = Options(**options)
        self.visible_links = []
        self.visibility_stage(Visibility.PEN)

        self.x_axis = self.add_pinned_point((self.radius, 0))

        self.alpha, self.beta = sympy.symbols("a b")

        alpha_start, beta_start = self.pen_coords_to_angles(pen_start)
        self.alpha_degrees = alpha_start

        # pin a, so it can serve as the input to the solver
        self.a = self.add_point(self.pen_leg_coords(alpha_start))
        self.pin_point(self.a)
        self.link_points(self.origin, self.a).length = self.pen_leg_length()

        self.b = self.add_point(self.pen_leg_coords(beta_start))
        self.link_points_with_length(self.origin, self.b, self.pen_leg_length())

        self.pen = self.paralellogram(self.origin, self.a, self.b)

        if self.visibility_stage(Visibility.PEN_PARALLELOGRAM):
            self.visible_links.remove(self.link_points(self.origin, self.x_axis))

    def pen_leg_length(self) -> float:
        return self.radius / 2

    def pen_leg_coords(self, degrees: float) -> numpy.array:
        return angle_to_coords(math.radians(degrees)) * self.pen_leg_length()

    def increase_alpha(self, degrees: float) -> None:
        self.alpha_degrees += degrees
        self.set_coords(self.a, self.pen_leg_coords(self.alpha_degrees))

    def symbolic_pen_coordinates(self) -> tuple[Expr, Expr, Symbol]:
        r = sympy.symbols("r")
        x = (r / 2) * sympy.cos(self.alpha) + (r / 2) * sympy.cos(self.beta)
        y = (r / 2) * sympy.sin(self.alpha) + (r / 2) * sympy.sin(self.beta)
        return x, y, r

    def pen_coords_to_angles(self, coords: Coords) -> tuple[float, float]:
        *expressions, r = self.symbolic_pen_coordinates()
        x_expression, y_expression = [expression.subs(r, self.radius) for expression in expressions]
        x, y = coords
        solutions = sympy.solve([x_expression - x, y_expression - y], self.alpha, self.beta)
        solutions = [solution for solution in solutions if all([angle.is_real for angle in solution])]
        assert len(solutions) > 0, "coords out of range"
        solution = solutions[1]
        alpha, beta = [math.degrees(float(angle)) for angle in solution]
        return alpha, beta

    def visibility_stage(self, *stages: list[Visibility]) -> bool:
        is_active = self.options.visible in stages
        if is_active:
            self.visible_links = self.link_map.links[:]
        return is_active

    def make_parallelogram(self, base: Point, a: Point, b: Point, tip: Point) -> None:
        base_a, base_b, a_tip, b_tip = self.link_point_pairs((base, a), (base, b), (a, tip), (b, tip))
        self.equal(base_a, b_tip)
        self.equal(base_b, a_tip)
        if self.options.brace_parallelograms:
            self.parallel(base_a, b_tip)

    def paralellogram(self, base: Point, a: Point, b: Point) -> Point:
        base_coords, a_coords, b_coords = self.all_coords(base, a, b)
        tip = self.add_point(a_coords + b_coords - base_coords)
        self.make_parallelogram(base, a, b, tip)
        return tip

    def make_contra_parallelogram(self, a: Point, b: Point, c: Point, d: Point) -> None:
        ab, bc, cd, da = self.link_point_pairs(*pairwise([a, b, c, d, a]))
        self.equal(ab, cd)
        self.equal(bc, da)
        if self.options.brace_contra_parallelograms:
            b_coords, d_coords = self.all_coords(b, d)
            intersection = self.add_point(interpolate(b_coords, d_coords, 0.5))
            b_intersection, d_intersection = self.link_point_pairs((b, intersection), (d, intersection))
            self.equal(b_intersection, d_intersection, unconstrained_ok = True)
            for crossing_link in [bc, da]:
                self.coincident(intersection, crossing_link)

    def contra_paralellelogram(self, a: Point, b: Point, c: Point) -> Point:
        a_coords, b_coords, c_coords = self.all_coords(a, b, c)
        ab = b_coords - a_coords
        ac_norm = normalize(c_coords - a_coords)
        ab_on_ac = numpy.dot(ab, ac_norm) * ac_norm
        d = self.add_point(c_coords + ab - 2 * ab_on_ac)
        self.make_contra_parallelogram(a, b, c, d)
        return d

    def multiply_angle(self, input: Point, base: Point, axis: Point, factor: int) -> Point:
        d = self.contra_paralellelogram(input, base, axis)
        current_input = input
        input_length, axis_length = self.get_lengths(input, axis, to = base)
        ratio = (input_length / axis_length) ** 2
        for _ in range(factor - 1):
            hinge = self.add_point_between(current_input, d, ratio)
            current_input = self.contra_paralellelogram(hinge, current_input, base)
            d = hinge
        return current_input

    def doubler(self, input: Point, double: Point, base: Point, axis: Point) -> None:
        d = self.contra_paralellelogram(input, base, axis)
        hinge = self.contra_paralellelogram(double, base, input)
        input_d = self.link_points(input, d)
        self.coincident(hinge, input_d)

    def additor(self, a: Point, b: Point, sum: Point, half_sum: Point, base: Point, axis: Point) -> None:
        self.doubler(half_sum, sum, base, axis)
        self.doubler(half_sum, a, base, b)

    def angles_to(self, *points: list[Point], base: Point) -> tuple[numpy.array, list[float]]:
        *all_coords, base_coords = self.all_coords(*points, base)
        angles = coords_to_angles(*[coords - base_coords for coords in all_coords])
        return angles, base_coords

    def add_angles(self, a: Point, b: Point, base: Point, axis: Point) -> Point:
        a_length, b_length, axis_length = self.get_lengths(a, b, axis, to = base)
        (a_angle, b_angle, axis_angle), base_coords = self.angles_to(a, b, axis, base = base)
        half_length = (a_length * b_length) ** 0.5
        half_sum = self.add_point(angle_to_coords(interpolate(a_angle, b_angle, 0.5)) * half_length + base_coords)
        sum_length = a_length * b_length / axis_length
        sum = self.add_point(angle_to_coords(a_angle + b_angle - axis_angle) * sum_length + base_coords)
        self.link_points_with_length(half_sum, base, half_length)
        self.link_points_with_length(sum, base, sum_length)
        self.additor(a, b, sum, half_sum, base, axis)
        return sum

    def subtract_angles(self, a: Point, b: Point, base: Point, axis: Point) -> Point:
        a_length, b_length, axis_length = self.get_lengths(a, b, axis, to = base)
        (a_angle, b_angle, axis_angle), base_coords = self.angles_to(a, b, axis, base = base)
        half_a_length = (a_length * axis_length) ** 0.5
        half_a = self.add_point(angle_to_coords(interpolate(a_angle, axis_angle, 0.5)) * half_a_length + base_coords)
        difference_length = a_length * axis_length / b_length
        difference = self.add_point(angle_to_coords(a_angle - b_angle + axis_angle) * difference_length + base_coords)
        self.link_points_with_length(half_a, base, half_a_length)
        self.link_points_with_length(difference, base, difference_length)
        self.additor(b, difference, a, half_a, base, axis)
        return difference

    def add_constant_angle(self, a: Point, radians: Expr, base: Point) -> Point:
        a_coords, base_coords = self.all_coords(a, base)
        degrees = float(radians * 180 / sympy.pi)
        a_link = self.link_points(a, base)
        length = a_link.get_length()
        point = self.add_point(angle_to_coords(coords_to_angle(a_coords - base_coords) + float(radians)) * length + base_coords)
        point_link = self.link_points_with_length(point, base, length)
        self.angle(a_link, point_link, degrees)
        self.link_points(point, a)
        return point

    def sum_angles(self, angle: Expr, base: Point, axis: Point) -> Point:
        assert angle.is_Add
        def should_sort_to_back(x) -> bool:
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

    def with_length(self, a: Point, length: float, base: Point) -> Point:
        a_coords, base_coords = self.all_coords(a, base)
        point = self.add_point(normalize(a_coords - base_coords) * length + base_coords)
        link = self.link_points_with_length(point, base, length)
        self.coincident(a, link)
        return point

    def vector_sum(self, base: Point, *vectors: list[Point]) -> Point:
        while len(vectors) > 0:
            new_base, *translatees = vectors
            vectors = [self.paralellogram(base, new_base, vector) for vector in translatees]
            base = new_base
        return base

    def move_curve(self, expression: Expr, x: Symbol, y: Symbol) -> Expr:
        x_coord, y_coord = self.coords(self.pen)
        solutions = sympy.solve(expression, y)
        assert len(solutions) > 0, "invalid curve"
        targets = [solution.subs(x, x_coord).evalf().as_real_imag() for solution in solutions]
        targets = [real for real, imag in targets if math.fabs(imag) < 1e-12]
        assert len(targets) > 0, f"curve needs to intersect x = {x_coord}"
        target_y = targets[0]
        return expression.subs(y, y + target_y - y_coord)

    def to_kempe_expression(self, expression: Expr, x: Symbol, y: Symbol) -> Expr:
        x_substitution, y_substitution, r = self.symbolic_pen_coordinates()
        substituted = expression.subs(x, x_substitution).subs(y, y_substitution)
        return TR0(TR5(TR8(TR0(substituted)))).rewrite(sympy.cos).subs(r, self.radius)

    def angle_to_vector(self, angle: Expr) -> Point:
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

    def constrain_to_y_axis(self, point: Point) -> None:
        link = self.link_points(point, self.origin)
        self.vertical(link)

    def from_curve(self, expression: Expr, x: Symbol, y: Symbol) -> None:
        # expression = self.move_curve(expression, x, y)
        expression = self.to_kempe_expression(expression, x, y)
        vectors = []
        constant_offset, scaled_cosines = expression.as_coeff_add(sympy.cos)
        if constant_offset != 0:
            vectors.append(self.add_pinned_point((constant_offset, 0)))
        for scaled_cosine in scaled_cosines:
            factor, (cosine,) = scaled_cosine.as_coeff_mul(sympy.cos)
            angle = cosine.args[0]
            vectors.append(self.with_length(self.angle_to_vector(angle), factor, self.origin))
        if self.visibility_stage(Visibility.COSINES):
            for vector in vectors:
                self.visible_links.remove(self.link_points(vector, self.origin))
        self.visibility_stage(Visibility.SCALED_COSINES)
        lock_onto_y_axis = self.vector_sum(self.origin, *vectors)
        self.constrain_to_y_axis(lock_onto_y_axis)
        self.visibility_stage(Visibility.ALL)
