import sympy
from sympy.simplify.fu import TR5, TR8, TR0
from pyslvs import VPoint
import matplotlib.pyplot as plt
from dataclasses import dataclass

alpha, beta, r, x, y = sympy.symbols("a b r x y")

def kempe(expression):
    x_substitution = (r / 2) * sympy.cos(alpha) + (r / 2) * sympy.cos(beta)
    y_substitution = (r / 2) * sympy.sin(alpha) + (r / 2) * sympy.sin(beta)
    substituted = expression.subs(x, x_substitution).subs(y, y_substitution)
    return TR5(TR8(TR0(substituted))).rewrite(sympy.cos)

# sympy.pprint(kempe(x ** 3 * y - 5 * y ** 2))

def interpolate(a: float, b: float, t: float):
    return a * (1 - t) + b * t

# copied from https://stackoverflow.com/a/55817881
def circle_circle_intersection(x0, y0, r0, x1, y1, r1):
    # circle 1: (x0, y0), radius r0
    # circle 2: (x1, y1), radius r1

    d=math.sqrt((x1-x0)**2 + (y1-y0)**2)

    # non intersecting
    if d > r0 + r1 :
        return None
    # One circle within other
    if d < abs(r0-r1):
        return None
    # coincident circles
    if d == 0 and r0 == r1:
        return None
    else:
        a=(r0**2-r1**2+d**2)/(2*d)
        h=math.sqrt(r0**2-a**2)
        x2=x0+a*(x1-x0)/d
        y2=y0+a*(y1-y0)/d
        x3=x2+h*(y1-y0)/d
        y3=y2-h*(x1-x0)/d

        x4=x2-h*(y1-y0)/d
        y4=y2+h*(x1-x0)/d

        return (x3, y3, x4, y4)

@dataclass
class Angle:
    a: VPoint
    b: VPoint
    c: VPoint

class Linkage:
    GROUND = "ground"
    points: list[VPoint]
    next_link_index: int

    def __init__(self):
        self.points = []
        self.next_link_index = 0

    def add_point(self, x: float, y: float) -> VPoint:
        links = ()
        join_type = 0
        angle = 0
        color = "green"
        point = VPoint(links, join_type, angle, color, x, y)
        self.points.append(point)
        return point

    def add_point_between(self, a: VPoint, b: VPoint, t: float) -> VPoint:
        x = interpolate(a.x, b.x, t)
        y = interpolate(a.y, b.y, t)
        point = self.add_point(x, y)
        self.link_points(point, a, b)
        return point

    def add_link(self, link_name: str, *points: list[VPoint]):
        for point in points:
            point.set_links(tuple(set([link_name, *point.links])))

    def next_link(self) -> str:
        link = "L" + str(self.next_link_index)
        self.next_link_index += 1
        return link

    def are_linked(self, *points: list[VPoint]) -> bool:
        all_links = [set(point.links) for point in points]
        intersection = all_links[0]
        for links in all_links[1:]:
            intersection = intersection.intersection(links)
        return len(intersection) > 0

    def link_points(self, *points: list[VPoint]):
        if self.are_linked(*points):
            return
        self.add_link(self.next_link(), *points)

    def pin_point(self, point: VPoint):
        self.add_link(self.GROUND, point)

    def add_pinned_point(self, *args, **kwargs):
        point = self.add_point(*args, **kwargs)
        self.pin_point(point)
        return point


class KempeLinkage(Linkage):
    def __init__(self, radius):
        super().__init__(self)
        self.radius = radius
        self.origin = self.add_pinned_point(0, 0)
        self.x_axis = self.add_pinned_point(self.radius, 0)

        between = self.add_point(0, self.radius / 2)
        self.link_points(self.origin, between)
        self.input = self.add_point(0, self.radius)
        self.link_points(between, self.input)

    def contra_paralellelogram(self, a: VPoint, b: VPoint, c: VPoint) -> VPoint:
        d_x = b.x - a.x + c.x
        d_y = b.y - a.y + c.y
        d = self.add_point(d_x, d_y)
        self.link_points(a, b)
        self.link_points(b, c)
        self.link_points(c, d)
        self.link_points(d, a)
        return d

    def translate(self, base: VPoint, input: VPoint, target: VPoint):
        base_copy = self.add_point(base.x + self.radius, base.y)
        input_copy = self.add_point(input.x + self.radius, input.y)
        target_copy = self.add_point(target.x + input.x - base.x, target.y + input.y - base.y)
        self.link_points(base, input)
        self.link_points(base_copy, input_copy)
        self.link_points(target, target_copy)
        self.link_points(base, base_copy)
        self.link_points(input, input_copy)
        self.link_points(target, target_copy)
        return target_copy


linkage = Linkage()
a = linkage.add_point(5, 5)
d = linkage.contra_paralellelogram(a, linkage.origin, linkage.x_axis)
linkage.link_points(a, d)
print(linkage.origin)
print(d)
# expr, inputs = example_list("Jansen's linkage (Single)")
# print(inputs)
# # Parse the mechanism expression into a list of joint data
# vpoints = parse_vpoints(expr)
# print(vpoints[0])
# print(get_vlinks([vpoints[0]]))
# # Config joint data and control data for the solver
# exprs = t_config(vpoints, inputs)
# # Solve the position
# xs, ys = [], []
# for angle in numpy.arange(0, 360, 0.01):
#     result = expr_solving(exprs, vpoints, {pair: angle for pair in inputs})
#     x, y = result[7]
#     xs.append(x)
#     ys.append(y)

# plt.plot(xs, ys)
# plt.show()
