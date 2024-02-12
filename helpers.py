import math
import numpy
from sympy import Expr, Matrix, Symbol, simplify
from sympy.polys.polytools import resultant
from type_aliases import Coords
from typing import TypeVar

T = TypeVar("T")

def interpolate(a: T, b: T, t: float) -> T:
    return a * (1 - t) + b * t

def normalize(array: numpy.array) -> numpy.array:
    return array / numpy.linalg.norm(array)

def coords_to_angle(point: Coords) -> float:
    angle = math.atan2(point[1], point[0])
    if angle < 0:
        angle += math.tau
    return angle

def coords_to_angles(*points: list[Coords]) -> list[float]:
    return [coords_to_angle(point) for point in points]

def angle_to_coords(radians: float) -> numpy.array:
    return numpy.array([math.cos(radians), math.sin(radians)])

# See https://en.wikipedia.org/wiki/Parametric_equation#Implicitization
def implicitize(x_coord: Expr, y_coord: Expr, t: Symbol, x: Symbol, y: Symbol) -> Expr:
    return resultant(x_coord - x, y_coord - y, t)

def bezier(t: Symbol, *points: list[Coords]) -> Matrix:
    assert len(points) >= 1, "bezier needs at least one point"
    # See https://en.wikipedia.org/wiki/B%C3%A9zier_curve#Recursive_definition
    def B(vectors: list[Matrix]) -> Matrix:
        if len(vectors) == 1:
            return vectors[0]
        return (1 - t) * B(vectors[:-1]) + t * B(vectors[1:])
    vectors = [Matrix(point) for point in points]
    return simplify(B(vectors))
