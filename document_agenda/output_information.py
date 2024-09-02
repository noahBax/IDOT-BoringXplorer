from typing import Literal, TypedDict


# Blame the census bureau if these are wrong
county_code_dict: dict[str, int] = {
    'Adams': 1,
    'Alexander': 3,
    'Bond': 5,
    'Boone': 7,
    'Brown': 9,
    'Bureau': 11,
    'Calhoun': 13,
    'Carroll': 15,
    'Cass': 17,
    'Champaign': 19,
    'Christian': 21,
    'Clark': 23,
    'Clay': 25,
    'Clinton': 27,
    'Coles': 29,
    'Cook': 31,
    'Crawford': 33,
    'Cumberland': 35,
    'De Kalb': 37,
    'De Witt': 39,
    'Douglas': 41,
    'Du Page': 43,
    'Edgar': 45,
    'Edwards': 47,
    'Effingham': 49,
    'Fayette': 51,
    'Ford': 53,
    'Franklin': 55,
    'Fulton': 57,
    'Gallatin': 59,
    'Greene': 61,
    'Grundy': 63,
    'Hamilton': 65,
    'Hancock': 67,
    'Hardin': 69,
    'Henderson': 71,
    'Henry': 73,
    'Iroquois': 75,
    'Jackson': 77,
    'Jasper': 79,
    'Jefferson': 81,
    'Jersey': 83,
    'Jo Daviess': 85,
    'Johnson': 87,
    'Kane': 89,
    'Kankakee': 91,
    'Kendall': 93,
    'Knox': 95,
    'Lake': 97,
    'LaSalle': 99,
    'Lawrence': 101,
    'Lee': 103,
    'Livingston': 105,
    'Logan': 107,
    'McDonough': 109,
    'McHenry': 111,
    'McLean': 113,
    'Macon': 115,
    'Macoupin': 117,
    'Madison': 119,
    'Marion': 121,
    'Marshall': 123,
    'Mason': 125,
    'Massac': 127,
    'Menard': 129,
    'Mercer': 131,
    'Monroe': 133,
    'Montgomery': 135,
    'Morgan': 137,
    'Moultrie': 139,
    'Ogle': 141,
    'Peoria': 143,
    'Perry': 145,
    'Piatt': 147,
    'Pike': 149,
    'Pope': 151,
    'Pulaski': 153,
    'Putnam': 155,
    'Randolph': 157,
    'Richland': 159,
    'Rock Island': 161,
    'St. Clair': 163,
    'Saline': 165,
    'Sangamon': 167,
    'Schuyler': 169,
    'Scott': 171,
    'Shelby': 173,
    'Stark': 175,
    'Stephenson': 177,
    'Tazewell': 179,
    'Union': 181,
    'Vermilion': 183,
    'Wabash': 185,
    'Warren': 187,
    'Washington': 189,
    'Wayne': 191,
    'White': 193,
    'Whiteside': 195,
    'Will': 197,
    'Williamson': 199,
    'Winnebago': 201,
    'Woodford': 203
}

class Header_Sheet_Entry(TypedDict):
    FILE_PATH: str
    API: int|str
    FARM_NAME: str
    Address: str
    COMPANY_NAME: Literal['IDOT']
    TYPE: Literal['ENG']
    COMP_DATE: str
    FARM_NUM: str  # boring number
    COUNTY: str
    COUNTY_CODE: int
    SEC: str
    TWP: str
    TDIR: str
    RNG: str
    RDIR: str
    MERIDIAN: str
    QUARTERS: str
    Elevation: str
    SurfaceWaterElev: str
    GroundwaterElev1stEncounter: str
    GroundWaterElevCompletion: str  # upon_completion
    GroundWaterElevAfterHours: str  # state_after_hours
    Hours: str  # hours_till_state
    Station: str  # boring station
    Offset: str  # boring offset

class Lithology_Sheet_Entry(TypedDict):
    API: int|str
    FARM_NAME: str
    FARM_NUM: str
    HBFORMATION_TOP: float
    HBFORMATION_BOTTOM: float
    HBFORMATION: str

class Blowcount_Sheet_Entry(TypedDict):
    API: int|str
    FARM_NAME: str
    FARM_NUM: str
    HB_Sample_Number: int
    HB_Sample_TOP: float
    HB_Sample_BOT: float
    HB_Lithology: int
    N: int

FULL_BLOWCOUNT_LIST = [
    "Map_Index",
    "API",
    "FARM_NAME",
    "FARM_NUM",
    "HB_Sample_Number",
    "HB_Sample_TOP",
    "HB_Sample_BOT",
    "HB_Sample_Type",
    "HB_Lithology",
    "N",
    "QP",
    "QU",
    "QU_Letter",
    "WATER_CONTENT(%)",
    "UNIT_DRY_WT"
]    

FULL_LITHOLOGY_LIST = [
    "Map_Index",
    "API",
    "FARM_NAME",
    "FARM_NUM",
    "HBFORMATION_TOP",
    "HBFORMATION_BOTTOM",
    "FORMATION_NAME",
    "HBFORMATION",
    "FACIES",
    "STRAT",
]
    

FULL_HEADER_LIST = [
    "Map_Index",
    "API",
    "FILE_PATH",
    "FARM_NAME",
    "Address",
    "COMPANY_NAME",
    "TYPE",
    "COMP_DATE",
    "FARM_NUM",
    "ENTERED_BY",
    "TOTAL_DEPTH",
    "LATITUDE",
    "LONGITUDE",
    "COUNTY",
    "COUNTY_CODE",
    "SEC",
    "TWP",
    "TDIR",
    "RNG",
    "RDIR",
    "MERIDIAN",
    "QUARTERS",
    "Elevation",
    "SurfaceWaterElev",
    "GroundwaterElev1stEncounter",
    "GroundWaterElevCompletion",
    "GroundWaterElevAfterHours",
    "Hours",
    "Station",
    "Offset",
    "Project/Job #",
    "VLQ",
    "VLC"
]
