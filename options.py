from dataclasses import dataclass
from enum import Enum, auto

class Visibility(Enum):
    PEN = auto()
    PEN_PARALLELOGRAM = auto()
    COSINES = auto()
    SCALED_COSINES = auto()
    COSINE_SUM = auto()
    ALL = COSINE_SUM

@dataclass
class Options:
    brace_parallelograms: bool = True
    brace_contra_parallelograms: bool = True
    visible: Visibility = Visibility.COSINES
