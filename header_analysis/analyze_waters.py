import logging
import re
from typing import TypedDict
from xplorer_tools.types import *
from detect_structure.helpers.find_descriptions.block_operations import *
from header_analysis.find_end_field import find_end_field
from header_analysis.parse_location import number_mistakes

logger = logging.getLogger(__name__)

class Water_Obj(TypedDict):
    surface_water_elv: str
    stream_bed_elev: str
    first_encounter: str
    upon_completion: str
    state_after_hours: str
    hours_till_state: str

def analyze_water(blocks: list[ocr_analysis]) -> Water_Obj:

    catch_surface_elev = re.compile(r'.*e[li1]e[vuy][.,]?[^a-z0-9]*', re.IGNORECASE)
    surface_elev = find_end_field(blocks, catch_surface_elev, 'surface water elev', True)
    surface_elev = __get_rid_of_units_if_no_numbers(surface_elev)
    surface_elev = __purge_no_data(surface_elev)
    logger.debug(f'Found water surface elevation "{surface_elev}"')

    catch_stream_elev = re.compile(r'.*e[li1]e[vuy][.,]?[^a-z0-9]*', re.IGNORECASE)
    stream_elev = find_end_field(blocks, catch_stream_elev, 'stream bed elev', True)
    stream_elev = __get_rid_of_units_if_no_numbers(stream_elev)
    stream_elev = __purge_no_data(stream_elev)
    logger.debug(f'Found stream bed elevation "{stream_elev}"')

    catch_first_encounter = re.compile(r'.*enc[o0][uvy]n[tf]er[^a-z0-9]*', re.IGNORECASE)
    first_encounter = find_end_field(blocks, catch_first_encounter, 'first encounter', True)
    first_encounter = __get_rid_of_units_if_no_numbers(first_encounter)
    first_encounter = __purge_no_data(first_encounter)
    logger.debug(f'Found first encounter at "{first_encounter}"')

    catch_upon_completion = re.compile(r'.*p[li1]e[tf][i1l][o0]n[^a-z0-9]*', re.IGNORECASE)
    upon_completion = find_end_field(blocks, catch_upon_completion, 'upon completion', True)
    upon_completion = __get_rid_of_units_if_no_numbers(upon_completion)
    upon_completion = __purge_no_data(upon_completion)
    logger.debug(f'Found upon completion "{upon_completion}"')

    after_hrs = __get_depth_after_hours(blocks)
    after_hrs = __get_rid_of_units_if_no_numbers(after_hrs)
    after_hrs = __purge_no_data(after_hrs)
    logger.debug(f'Found after hours "{after_hrs}"')

    hours_state = __get_hours_till_state(blocks)
    hours_state = __check_hours_is_date(hours_state)
    hours_state = __get_rid_of_units_if_no_numbers(hours_state)
    logger.debug(f'Found hours till state "{hours_state}"')

    ret: Water_Obj = {
        'surface_water_elv': surface_elev,
        'stream_bed_elev': stream_elev,
        'first_encounter': first_encounter,
        'upon_completion': upon_completion,
        'state_after_hours': after_hrs,
        'hours_till_state': hours_state
    }
    return ret


def __get_depth_after_hours(blocks: list[ocr_analysis]) -> str:

    after_hrs_line = limit_to_line(blocks, re.compile(r'a[ft][tf].*[hN]r[s$]', re.IGNORECASE))

    # Get rid of hrs and everything before it
    feet = re.sub(r'.*hr[s$][^a-z0-9]*', '', after_hrs_line, flags=re.IGNORECASE)

    return feet

def __get_hours_till_state(blocks: list[ocr_analysis]) -> str:

    after_hrs_line = limit_to_line(blocks, re.compile(r'a[ft][tf].*[hN]r[s$]', re.IGNORECASE))

    # Get rid of after and before and hrs and after
    hours = re.sub(r'.*a[ft][tf]er?\s*', '', after_hrs_line, flags=re.IGNORECASE)
    hours = re.sub(r'\s*hr[s$].*', '', hours, flags=re.IGNORECASE)

    return hours

def limit_to_line(blocks: list[ocr_analysis], pattern: re.Pattern):
    blocks.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

    has_cool = [b for b in blocks if re.search(pattern, b['text'])]

    if len(has_cool) == 0:
        return ''
    else:
        logger.debug(f'Found *something* in {[b["text"] for b in has_cool]}')
        field_block = has_cool[0]

    top_bound = top_of_ocr_coords(field_block['coords_group']) - 6
    low_bound = bottom_of_ocr_coords(field_block['coords_group']) + 6 

    def check_within(block: ocr_analysis):
        center = center_ocr_coords(block['coords_group'])
        return center[1] > top_bound and center[1] < low_bound
    
    important = [ b for b in blocks if check_within(b) ]
    important.sort(key=lambda b: left_of_ocr_coords(b['coords_group']))

    line_str = ' '.join([b['text'] for b in important])
    logger.debug(f'*something* expanded to {line_str}')

    return line_str

def __purge_no_data(line: str) -> str:

    if re.search(r'n[o0]\s*[d0o]ata', line, flags=re.IGNORECASE):
        return ''
    elif re.search(r'N[/l71|I]A', line) or re.match(r'NA', line):
        return 'N/A'
    elif len(line) < 3:
        return ''
    else:
        return line

def __get_rid_of_units_if_no_numbers(line: str) -> str:

    has_nums = sum([l.isdigit() for l in line])

    if has_nums <= 2:
        # Remove ft (or m)
        line = re.sub(r'\s*(ft\.?|(m|rn)(m|rn)?)$', '', line, flags=re.IGNORECASE)
    else:
        for k in number_mistakes:
            line = line.replace(k, number_mistakes[k])
            line = re.sub(r'(?<=\d)[.,]+(?=[ft(m|rn)])', ' ', line)

        # Get rid of any non-number characters before the numbers
        line = re.sub(r'^\D+(?=\d)', '', line)

        # Add a space in between feet or meters
        line = re.sub(r'(?<=\d)(?=ft|mm)', ' ', line, flags=re.IGNORECASE)

    return line

def __check_hours_is_date(line: str) -> str:

    scan = re.search(r'[D0o]a[yvu][s$]?', line, flags=re.IGNORECASE)
    if scan and scan.start(0) > 0:
        
        logger.debug(f'Fixing hours string: {line}')
        # Correct all numbers before the first instance of Days
        number_string = line[:scan.start(0)].strip()
        for k in number_mistakes:
            number_string = number_string.replace(k, number_mistakes[k])
        
        ret = number_string + ' ' + 'Days' + line[scan.end(0):]

    else:
        ret = line

    # Get rid of trailing .'s
    ret = re.sub(r'[.,\s]+$', '', ret)

    return ret