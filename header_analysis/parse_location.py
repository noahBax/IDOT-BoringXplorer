"""
Want to find
 - Section (sec)
 - Township (twp)
 - Township direction (tdir)
 - range (rng)
 - range direction (rdir)
 - meridian (3pm for example)
 - Quarters if we can
"""

import logging
import re
from typing import TypedDict

logger = logging.getLogger(__name__)

number_mistakes = {
    'G': '6',
    'b': '6',
    'I': '1',
    'i': '1',
    'L': '1',
    'l': '1',
    'O': '0',
    'o': '0',
    'g': '9',
    'A': '4',
}

# Only purpose in this file is to fix directions
letter_mistakes = {
    '$': 'S',
    '5': 'S'
}

class location_info(TypedDict):
    sec: str
    twp: str
    tdir: str
    rng: str
    rdir: str
    meridian: str
    quarters: str


def parse_location(raw: str) -> location_info:

    def fix_numbers(s: str) -> str:
        for k in number_mistakes:
            s = s.replace(k, number_mistakes[k])
        return s

    def fix_letters(s: str) -> str:
        for k in letter_mistakes:
            s = s.replace(k, letter_mistakes[k])
        return s

    # demo = 'NE 1/4, SEc. 7, twp. 18 N, rng. 7 W, 3 pm'
    # demo = 'NE 1/4,SEc.7twp.18N,rng7W,3pm'
    # raw = demo

    # Just do a quick sanity check. Sometimes the guy putting numbers into the
    # computer says "Nope" and just doesn't and it fucks everything you've made
    # up. (Check out Adams County/001-0019 SOIL 2002.pdf). Idk how many other
    # components I've made will just break when this happens


    # Sanity check=look for numbers
    # Also fail if location was an empty string
    if sum([r.isdigit() for r in raw]) == 0 or raw == '':
        logger.warn('location field is empty')
        ret: location_info = {
            'sec': '',
            'twp': '',
            'tdir': '',
            'rng': '',
            'rdir': '',
            'meridian': '',
            'quarters': ''
        }

        return ret

    section_sig = re.compile(r'(?<=[s$]ec).*(?=twp)', re.IGNORECASE)
    township_sig = re.compile(r'(?<=twp).*(?=rng)', re.IGNORECASE)
    range_sig = re.compile(r'(?<=rng).*(?=\d+)', re.IGNORECASE)
    meridian_sig = re.compile(r'(?<=rng.{3}).*(?=pm|am)', re.IGNORECASE)
    quarters_sig = re.compile(r'([n(s|$)][ew]\s*){1,3}(?=1.4)|([ns$ew]\s*(?=1.2))', re.IGNORECASE)  # Signature includes 1/4's and 1/2's

    # First find the section stuff
    section_loc = re.search(section_sig, raw)
    if not section_loc:
        raise Exception('Could not find "SEC." in location string')
    
    township_loc = re.search(township_sig, raw)
    if not township_loc:
        raise Exception('Could not find "TWP." in location string')

    range_loc = re.search(range_sig, raw)
    if not range_loc:
        raise Exception('Could not find "RNG" in location string')

    meridian_loc = re.search(meridian_sig, raw)
    if not meridian_loc:
        raise Exception('Could not find "PM" or "AM" in location string')

    quarters_loc = re.search(quarters_sig, raw)
    if not quarters_loc:
        logger.warning('Could not find viable section info in location string')


    # The section number is the only number between SEC and TWP
    contains_section = section_loc.group(0)
    contains_section = fix_numbers(contains_section)

    section_arr = re.findall(r'\d', contains_section)

    if len(section_arr) == 0:
        raise Exception('There were no numbers in the section field of location string')

    section_num = ''.join(section_arr)


    # Find the township and township number
    contains_twp = township_loc.group(0)
    contains_twp = fix_numbers(contains_twp)

    twp_num_arr = re.findall(r'\d', contains_twp)
    twp_letter_arr = re.findall(r'[A-Z]', contains_twp.upper())

    twp_num = ''.join(twp_num_arr)
    twp_dir = ''.join(twp_letter_arr)


    # Find the range and range number
    contains_rng = range_loc.group(0)
    contains_rng = fix_numbers(contains_rng)

    rng_num_arr = re.findall(r'\d', contains_rng)
    rng_letter_arr = re.findall(r'[A-Z]', contains_rng.upper())

    rng_num = ''.join(rng_num_arr)
    rng_dir = ''.join(rng_letter_arr)


    # Find the meridian number
    contains_meridian = meridian_loc.group(0)
    contains_meridian = fix_numbers(contains_meridian)

    meridian_arr = re.findall(r'\d', contains_meridian)
    meridian = ''.join(meridian_arr)


    # Now handle quarters
    if quarters_loc:
        quarters = quarters_loc.group(0)
        quarters = fix_letters(quarters).strip()
    else:
        quarters = ''
    # I just want to make sure that these are formatted with spaces. Sometimes
    # ocr doesn't pick up on them.
    split_on_me = re.compile(r'(?<=[ew])\s*(?=[n(s|$)])', re.IGNORECASE)
    quarter_parts = re.split(split_on_me, quarters)
    quarters = ' '.join(quarter_parts)


    ret: location_info = {
        'sec': section_num,
        'twp': twp_num,
        'tdir': twp_dir,
        'rng': rng_num,
        'rdir': rng_dir,
        'meridian': meridian,
        'quarters': quarters
    }

    return ret