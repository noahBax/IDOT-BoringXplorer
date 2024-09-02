from typing import TypedDict
from enum import Enum, auto

class Coordinate(TypedDict):
    x: float
    y: float

class Vector(TypedDict):
    x: float
    y: float

class form_types(Enum):
    BBS_137_REV_8_99 = auto()
    BD_137_REV_9_60 = auto()
    BD_137_REV_4_78 = auto()
    Empty = auto()

coord_pair = tuple[float, float]
confidence = float
ocr_coords = tuple[coord_pair, coord_pair, coord_pair, coord_pair]
ocr_result = tuple[
    ocr_coords,
    tuple[str, confidence]
]
simple_result = tuple[
    str, float
]

class ocr_analysis(TypedDict):
    coords_group: ocr_coords
    text: str
    confidence: float
    page_offset: Coordinate

class PageHeader(TypedDict):
    route: str
    description: str
    logged_by: str
    section: str
    location: str
    county: str
    drilling_method: str
    hammer_type: str
    struct_no: str
    station: str
    boring_no: str
    offset: str
    ground_surface_elev: str