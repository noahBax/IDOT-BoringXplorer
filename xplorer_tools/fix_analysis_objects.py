import logging
from header_analysis.analyze_header import Header_Obj
from header_analysis.analyze_waters import Water_Obj
from collections import Counter

"""
The Header_Obj and Water_Obj are produced on every page in a single boring
report. Sometimes information can't be captured by OCR for whatever reason and
it needs to be filled in with information from a different document. I think the
simplest way to do that is just take a majority vote of which page thinks a
field is this or that.
"""

logger = logging.getLogger(__name__)

def take_majority_header(objs: list[Header_Obj]) -> Header_Obj:

    logger.debug(f'Doing {objs}')
    
    ret = {}
    ret['page_num'] = -1  # Don't care about output of this
    ret['page_total'] = -1
    string_fields = [
        'route',
        'description',
        'logged_by',
        'section',
        'location',
        'county',
        'drilling_method',
        'hammer_type',
        'struct_no',
        'struct_station',
        'boring_no',
        'boring_station',
        'offset',
        'ground_surface_elev',
        'date_str',
    ]
    for field in string_fields:
        options: list[str] = [o[field] for o in objs if o[field].strip() != '']
        if len(options) == 0:
            ret[field] = ''
        else:
            ret[field] = Counter(options).most_common(1)[0][0]

    loc = {}
    loc_fields = [
        'sec',
        'twp',
        'tdir',
        'rng',
        'rdir',
        'meridian',
        'quarters',
    ]
    for field in loc_fields:
        options: list[str] = [o['location_obj'][field] for o in objs if o['location_obj'][field].strip() != '']
        if len(options) == 0:
            loc[field] = ''
        else:
            loc[field] = Counter(options).most_common(1)[0][0]
    ret['location_obj'] = loc

    return ret  # type: ignore

def take_majority_water(objs: list[Water_Obj]) -> Water_Obj:

    if len(objs) == 1:
        return objs[0]
    
    ret = {}
    fields = [
        'surface_water_elv',
        'stream_bed_elev',
        'first_encounter',
        'upon_completion',
        'state_after_hours',
        'hours_till_state',
    ]
    for field in fields:
        options: list[str] = [o[field] for o in objs if o[field].strip() != '']
        if len(options) == 0:
            ret[field] = ''
        else:
            ret[field] = Counter(options).most_common(1)[0][0]
    return ret  # type: ignore