from difflib import SequenceMatcher
import logging
import re
from header_analysis.find_route import find_route
from header_analysis.find_description import find_desc
from header_analysis.find_logged import find_logger
from header_analysis.find_section import find_section
from header_analysis.find_location import find_location
from header_analysis.find_county import find_county
from header_analysis.find_drill import find_drill
from header_analysis.find_both_stations import find_both_stations
from header_analysis.find_end_field import find_end_field
from header_analysis.parse_location import location_info, parse_location
from header_analysis.find_pages import find_pages
from xplorer_tools.types import *
from document_agenda.output_information import county_code_dict
from header_analysis.find_date import find_date

logger = logging.getLogger(__name__)


class Header_Obj(TypedDict):
    route: str
    description: str
    logged_by: str
    section: str
    location: str
    county: str
    drilling_method: str
    hammer_type: str
    struct_no: str
    struct_station: str
    boring_no: str
    boring_station: str
    offset: str
    ground_surface_elev: str
    location_obj: location_info
    date_str: str
    page_num: int|None
    page_total: int|None

def analyze_header(blocks: list[ocr_analysis], known_page: int | None, known_page_limit: int | None) -> Header_Obj:
    route = find_route(blocks)
    logger.debug(f'Found route "{route}"')

    desc = find_desc(blocks)
    logger.debug(f'Found description "{desc}"')

    log_by = find_logger(blocks)
    logger.debug(f'Found logged by "{log_by}"')

    section = find_section(blocks)
    logger.debug(f'Found section "{section}"')

    location = find_location(blocks)
    logger.debug(f'Found location "{location}"')

    county = find_county(blocks)
    county = __fix_county(county)
    logger.debug(f'Found county "{county}"')

    drill_method = find_drill(blocks)
    logger.debug(f'Found drill "{drill_method}"')
    
    catch_hammer = re.compile(r'.*[hm]ammer t[yvu]pe\s*', re.IGNORECASE)
    hammer_type = find_end_field(blocks, catch_hammer, 'hammer type', True)
    logger.debug(f'Found hammer type "{hammer_type}"')

    struct_station, boring_station = find_both_stations(blocks)
    logger.debug(f'Found struct station "{struct_station}"')
    logger.debug(f'Found boring station "{boring_station}"')

    catch_struct_no = re.compile(r'.*[s$][tf]ruc[tf][,:.]?\s*n[o0][:,.]?\s*', re.IGNORECASE)
    struct_no = find_end_field(blocks, catch_struct_no, 'struct no', True)
    logger.debug(f'Found struct no "{struct_no}"')

    catch_boring_no = re.compile(r'.*[bs8][o0]r[il1]ng[\s\.,]*n[o0]\.?\s*', re.IGNORECASE)
    boring_no = find_end_field(blocks, catch_boring_no, 'boring no', True)
    boring_no = boring_no.replace('$', 'S')
    logger.debug(f'Found boring no "{boring_no}"')

    catch_offset = re.compile(r'.*[o$][ft][ft]set\s*', re.IGNORECASE)
    offset = find_end_field(blocks, catch_offset, 'offset', True)
    logger.debug(f'Found offset "{offset}"')

    catch_ground_elev = re.compile(r'.*gr[o0]u..?d\s*[s$]urface\s*e[li1t]e[vyu]\.?\s*', re.IGNORECASE)
    ground_elev = find_end_field(blocks, catch_ground_elev, 'ground surface elev', True)
    ground_elev = re.sub(r'^[., ]*', '', ground_elev)
    logger.debug(f'Found ground surface elev "{ground_elev}"')

    # Get individual fields out of the location string
    location_obj = parse_location(location)
    logger.debug('Location object:')
    logger.debug(location_obj)

    date = find_date(blocks)

    if known_page == None or known_page_limit == None:
        guess_num, guess_total = find_pages(blocks)
        page_num = guess_num if known_page == None else known_page
        page_total = guess_total if known_page_limit == None else known_page_limit
    else:
        page_num, page_total = known_page, known_page_limit

    ret: Header_Obj = {
        'route': route,
        'description': desc,
        'logged_by': log_by,
        'section': section,
        'location': location,
        'county': county,
        'drilling_method': drill_method,
        'hammer_type': hammer_type,
        'struct_no': struct_no,
        'struct_station': struct_station,
        'boring_no': boring_no,
        'boring_station': boring_station,
        'offset': offset,
        'ground_surface_elev': ground_elev,
        'location_obj': location_obj,
        'date_str': date,
        'page_num': page_num,
        'page_total': page_total
    }

    return ret

def __fix_county(guess: str):

    guess = guess.lower()

    if guess in county_code_dict or guess == '':
        return guess

    # Need to find the closest county to the misspelled string
    def similar(a: str, b: str):
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    closest_county = max(county_code_dict.keys(), key=lambda name: similar(name, guess))
    return closest_county
