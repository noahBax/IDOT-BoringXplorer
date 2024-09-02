import logging
import re
import numpy as np
from math import floor
from paddleocr import PaddleOCR
from skimage.io import imsave
from detect_structure.helpers.find_BUM_info.BUM_pair import Pair
from detect_structure.helpers.find_BUM_info.blowcount import BlowCount
from detect_structure.helpers.soil_depth_ruler.soil_depth_ruler import Soil_Depth_Ruler
from document_agenda.document_agenda import Document_Agenda
from tools.types import ocr_analysis, simple_result
from detect_structure.helpers.find_descriptions.ocr_operations import possible_mistakes
from tools.cleanup_side import clean_side
from log_config import logger_num

logger = logging.getLogger(__name__)
save_count = 0

def _look_for_texts(colored_blows: np.ndarray, pair: Pair, ocr_instance: PaddleOCR, soil_ruler: Soil_Depth_Ruler, fail_count=0) -> list[int]:
    """
    `fail_count` is to specify the amount of times that ocr can return no
    results
    """

    global save_count

    logger.debug(f'Looking between {pair.top_bound} and {pair.low_bound}')

    sections: list[tuple[int, int]]
    topper = floor(soil_ruler.ask_for_pixels(pair.top_bound))
    lower = floor(soil_ruler.ask_for_pixels(pair.low_bound))
    if pair.span == 0.5 and pair.might_extend_more:
        y1 = topper
        y2 = lower
        d = y2-y1
        y3 = y2+d
        sections = [(y1-1, y2-2), (y2-1, y3-2)]
    elif pair.span == 0.5:
        y1 = topper
        y2 = lower
        sections = [(y1,y2-4)]
    elif pair.span == 1.0:
        y1 = topper
        y3 = lower
        y2 = floor((y3 - y1) / 2) + y1
        sections = [(y1+1, y2-2), (y2-1, y3-2)]
    elif pair.span == 1.5:
        y1 = topper
        y4 = lower
        jump = (y4 - y1) / 3
        y2 = floor(y1 + jump)
        y3 = floor(y1 + 2*jump)
        sections = [(y2-2, y3-4), (y3-2, y4-4)]
        # sections = [(y1, y2), (y2, y3), (y3, y4)]
    else:
        raise Exception('Unhandled pair span')

    ret: list[int] = []
    logger.debug(f'Looking for text in sections {sections}')
    for a, b in sections:
        logger.debug(f'Cropping between {a} and {b}')
        cropped = colored_blows[a:b]
        # imsave(f'logs/last_simple{logger_num}.png', cropped)
        
        # Cut out the gunk around the edges
        cropped = clean_side(cropped, leeway=5, ratio=0.65)
        cropped = clean_side(cropped, side=4, leeway=7, ratio=0.7)
        cropped = clean_side(cropped, side=2, leeway=7, ratio=0.7)
        # imsave(f'simple_texts/last_simple{save_count}.png', cropped)
        
        results = ocr_instance.ocr(cropped, cls=False, det=False)[0]

        if results == None:
            fail_count -= 1
            if fail_count < 0:
                raise Exception('Could not recognize text')
            else:
                continue

        logger.debug('OCR results')
        logger.debug(results)

        save_count += 1

        # look_at_text = draw_ocr_text_bounds(results, cropped)
        # imsave(os.path.join('visuals', f'last_looked.png'), look_at_text)

        text_results = _fix_ocr_results(results, check_number=False)

        # Recognized "inches"
        if len(text_results) > 0 and text_results[0] == -2:
            if len(ret) > 0:
                ret.pop()
            continue

        logger.debug(f'Found, {text_results}')

        ret += text_results
        if len(ret) == 1 and len(text_results) > 0 and text_results[0] == 100:
            logger.debug('Okay now exiting')
            break

    return ret

def _fix_ocr_results(ocr_results: list[simple_result], check_number=True):
    """
    What makes this function different from the non-simple version is that it
    takes a list of simple_result's AND has some additional replacements
    """

    def try_number(s: str):
        try:
            int(s)
        except ValueError:
            raise Exception(f'OCR recognized non-number string:', s)

    ret: list[int] = []

    # First modify the OCR results
    for index, result in enumerate(ocr_results):
        
        corrected_text: str = result[0]

        # Remove negatives. Everywhere. Because it's a robot
        # corrected_text = re.sub(r'[-.~" *\']+(?=\d)', '', corrected_text)
        corrected_text = re.sub(r'[^a-zA-Z0-9\/]+(?=\d)', '', corrected_text)
        corrected_text = re.sub(r'(?<=\d)[.* ,]+', '', corrected_text)

        if len(corrected_text) == 0 or sum(c.isdigit() for c in corrected_text) == 0:
            logger.debug('There were no numbers in this string')
            return [0]

        if re.match(r'[HP]', corrected_text):
            logger.debug('Matched "H" or "P"')
            return [0]

        if corrected_text[-1] == '/' or re.match(r'"[//1lI]$', corrected_text):
            logger.debug('Matched cases we are markers to throw away')
            continue

        # Try to match W.O.H
        if re.search(r'[wnm][.,][o0][.,]h.?$', corrected_text, flags=re.IGNORECASE):
            logger.debug('Matched W.O.H.')
            return [0]

        # Try to match W.O.P
        if re.search(r'[wnm][.,][o0][.,][ps].?$', corrected_text, flags=re.IGNORECASE):
            logger.debug('Matched W.O.P.')
            return [0]

        # Add in a 0 to the beginning of the string. This is meant to just help
        # deal with one specific edge case. It will not affect any of the logic
        # and will immediately get handled by the int conversion
        corrected_text = '0' + corrected_text
        
        # Extra specks can be interpreted as colons. Only do it if the
        # confidence is relatively lower though
        if result[1] < 0.95:
            logger.debug(f'Removing colons from the string "{result[0]}"')
            corrected_text = re.sub(r'[:;ij]', '', corrected_text)
                    
        # Replace possible mistakes
        for k in possible_mistakes:
            corrected_text = corrected_text.replace(k, possible_mistakes[k])

        # Sometimes, this is done to say the amount of inches blown instead of
        # the other normal way (frankly I think this is more sane, but whatevs)

        # Make sure to catch 1's 7's and l's as the slash
        corrected_text = re.sub(r'(?<=\d)\/\d*["\'!]?|(?<=\d)[\/l]\d+["\'!].*', '', corrected_text)

        # Some beautiful geniuses like to put /5 on one line and then "inches"
        # on the next. Wtf

        # Recognize the 'nch' part of inch(es)
        if re.search(r'[nh]c[hn]', corrected_text, re.IGNORECASE):
            logger.debug('Found a genius')
            return [-2]

        # Check to see if whatever is left of the string besides the added 0 is
        # just junk
        if not corrected_text[1:].isnumeric():
            return [0]

        # And check to see if it can be represented as a number
        if check_number:
            try_number(corrected_text)

        i = int(corrected_text)

        if i > 100:
            # Need to drop the first digit greater than 0 and put that.
            corrected_text = re.sub(r'0*1(?=\d{2})', '', corrected_text)
            i = int(corrected_text)

        logger.debug(f'Resulting string: {corrected_text}')
        
        ret.append(i)
        if i == 100:
            logger.debug('Found 100 blows, exiting early')
            break
    
    return ret


def analyze_pairs(pairs: list[Pair],
                  blow_bounds: list[float],
                  colored_blows: np.ndarray,
                  soil_ruler: Soil_Depth_Ruler,
                  document_agenda: Document_Agenda,
                  ocr_analyze_pairs: PaddleOCR) -> list[BlowCount]:

    ret: list[BlowCount] = []

    for pair in pairs:
        logger.debug(f'Analyzing pair: {pair}')
        
        if pair.imaginary:

            numbers = _look_for_texts(colored_blows, pair, ocr_analyze_pairs, soil_ruler, fail_count=1)

            if len(numbers) > 0:
                ret.append(BlowCount(pair, numbers, document_agenda))
            
        elif pair.span == 0.5 and pair.might_extend_more:

            numbers = _look_for_texts(colored_blows, pair, ocr_analyze_pairs, soil_ruler, fail_count=1)

            if len(numbers) == 0:
                raise Exception('Pair was expected to have at least 1 number')

            ret.append(BlowCount(pair, numbers, document_agenda))
            
        elif pair.span == 1.0 and not pair.top_pair:
            # Normal case: pair spans 1 foot and is in the middle
            
            numbers = _look_for_texts(colored_blows, pair, ocr_analyze_pairs, soil_ruler)

            if len(numbers) == 1 and numbers[0] == 100:
                logger.debug('Pair unexpectedly had 100 blows in under 6 inches')
            elif len(numbers) == 0:
                logger.critical('There were no numbers in a blow count section')
                logger.critical('A likely story is that the inches depth marker took up everything and there are 100 blows above it')
                logger.critical('I am making that assumption, but this should really have code that checks it')
                numbers = [100]
            elif len(numbers) != 2:
                logger.debug(f'Pair expected to have two numbers: {numbers}, there must have been inches')
            
            ret.append(BlowCount(pair, numbers, document_agenda))
            
        elif pair.span == 1.0 and pair.top_pair:
            # Special case: top blow count entry should extend down 1/2 foot

            blow_bounds.sort()
            if blow_bounds[1] != pair.low_bound + 0.5:
                logger.warning(f'blow_bounds: {blow_bounds}')
                logger.warning(f'Pair low bound : {pair.low_bound}')
                logger.warning('Top bound does not follow normal format')
                new_pair = pair
                numbers = _look_for_texts(colored_blows, new_pair, ocr_analyze_pairs, soil_ruler)
                if len(numbers) == 1 or len(numbers) == 2 and numbers[1] == 0:
                    logger.warning('Pair just had a depth marker after')
                    new_pair = Pair(pair.top_bound, pair.low_bound - 0.5)
                    new_pair.incomplete = True
            else:
                new_pair = Pair(pair.top_bound, blow_bounds[1])
                numbers = _look_for_texts(colored_blows, new_pair, ocr_analyze_pairs, soil_ruler)
            
            ret.append(BlowCount(new_pair, numbers, document_agenda))

        elif pair.span < 1.0 and (pair.bottom_pair or pair.top_pair):
            # Incomplete case: top/bottom entry that extends to the prev/next
            # column
            
            numbers = _look_for_texts(colored_blows, pair, ocr_analyze_pairs, soil_ruler)

            if len(numbers) != 1:
                raise Exception(f'Pair expected to have one number: {numbers}')
            
            pair.incomplete = True
            ret.append(BlowCount(pair, numbers, document_agenda))

        elif pair.span < 1.0:
            # Last entry: some last entries appear as incomplete

            numbers = _look_for_texts(colored_blows, pair, ocr_analyze_pairs, soil_ruler)

            if len(numbers) != 1:
                raise Exception(f'Pair expected to have one number: {numbers}')
            
            blow = BlowCount(pair, numbers, document_agenda)
            blow.last_BUM = True  # Mark it as such
            ret.append(blow)

        else:
            raise Exception('Unhandled case when analyzing pairs')

    logger.debug('Performed analysis:')
    logger.debug(ret)

    return ret