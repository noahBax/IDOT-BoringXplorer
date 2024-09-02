from configparser import ConfigParser
import multiprocessing
import multiprocessing.process
import os
import datetime
import time
import concurrent.futures
from header_analysis.simply_get_page_groups import Page_Group_Builder
from manage_outputs.manage_outputs import Output_Manager
from document_agenda.output_information import Header_Sheet_Entry, Lithology_Sheet_Entry, Blowcount_Sheet_Entry
from xplorer_tools.compile_ideal_batches import compile_ideal_batches, Ideal_Batch
import numpy as np

import logging
import sys

def get_pdfs(dir: str) -> list[str]:
    pdfs = []

    if not os.path.exists(dir):
        logger.critical('RAN into an issue!')
        logger.critical('Could not find that directory!')
        sys.exit()

    for dirpath, dirnames, filenames in os.walk(dir):
        for file in filenames:
            if file.lower().endswith('.pdf'):
                pdfs.append(os.path.join(dirpath, file))
    
    return pdfs

def get_page_count_dict(queue, paths: list[str]) -> None:
    from xplorer_tools.find_page_count_dict import find_page_count_dict
    ret = find_page_count_dict(paths)
    queue.put(ret)


logger = logging.getLogger(__name__)
def main():

    logger.info(f'Start time is {datetime.datetime.now()}')

    config = ConfigParser()
    config.read('config.ini')
    
    pdfs_folder = config['BEHAVIOR']['PDFsParentFolder']
    logger.info(f'Looking for pdfs under {pdfs_folder}')

    pdfs = get_pdfs(pdfs_folder)
    logger.info(f'Found {len(pdfs)} pdfs to analyze')

    out_putter = Output_Manager(config)
    if not out_putter.success:
        raise Exception('Output Manager failed to initialize')

    logger.info('Finding pdf lengths')

    queue = multiprocessing.Queue()
    getting_pages = multiprocessing.Process(target=get_page_count_dict, args=(queue, pdfs,))
    getting_pages.start()
    page_count_dict = queue.get()
    getting_pages.join()


    # # Batch into 20
    # batch_size = 20
    # batches = zip_longest(*[iter(pdfs)]*batch_size, fillvalue='')
    temp = [[r'./AnalyzingReports/IDOT_Dist6_Borings\Sangamon County North of I-72 (includes I-72)\084-0149 SOIL 1972.pdf']]
            #  ,
            #  r'./AnalyzingReports/IDOT_Dist6_Borings\Sangamon County North of I-72 (includes I-72)\084-0516 SOIL 2003.pdf'
            #  r'./AnalyzingReports/IDOT_Dist6_Borings\Morgan County\069-0511 SOIL-ROCK 2001.pdf
            # 
            # ,
            #  r'./AnalyzingReports/IDOT_Dist6_Borings\Sangamon County North of I-72 (includes I-72)\M-326 Overhead Sign Truss for 6th St Ramp from WB I-72.pdf,
            #  r'./AnalyzingReports/IDOT_Dist6_Borings\Hancock County\034-0066 SOIL 2002.pdf'
            #  r'./AnalyzingReports/IDOT_Dist6_Borings\Brown County\005-0500 SOIL-ROCK 2007.pdf'

    logger.info('Compiling ideal batches')
    batches = compile_ideal_batches(page_count_dict, config, max_pages_per_batch=72)

    all_paths = [path for batch in batches for path in batch['paths']]
    if len(all_paths) != len(pdfs):
        raise Exception(f'Batcher had different number of docs: {len(all_paths)}. Should be {len(pdfs)}')

    logger.info('Start X-ploring')

    # test_file_till_error(r'./AnalyzingReports/IDOT_Dist6_Borings\Hancock County\034-2527 SOIL 2010.pdf')
    # # test_file_till_error(r'./AnalyzingReports/IDOT_Dist6_Borings\Morgan County\069-0521 SOIL 2007.pdf')
    # return

    fail_batch: Ideal_Batch = {
        'max_workers': 1,
        'paths': []
    }
    
    cumulative_time = 0
    total_processed = 0
    for batch_index, batch in enumerate(batches):

        logger.info(f'batch {batch_index+1} of {len(batches)}')
        
        # Handle the batch
        new_time, failed = handle_batch(batch, total_processed, out_putter)
        cumulative_time += new_time
        
        # Retry these later
        fail_batch['paths'].extend(failed)
        
        # Clean up
        total_processed += len(batch['paths'])
        logger.info('Sleeping...')
        time.sleep(15)
        logger.info('Alarm alarm alarm')

    # Do the stuff that failed the first time
    logger.info('Trying failed items')
    new_time, failed = handle_batch(fail_batch, total_processed, out_putter)


    logger.info(f'Cumulative time was {cumulative_time} seconds')
    logger.info(f'Average time per process was {cumulative_time / len(pdfs)}')

    logger.info(f'End time is {datetime.datetime.now()}')

def handle_batch(batch: Ideal_Batch, prior_processed: int, out_putter: Output_Manager | None) -> tuple[int, list[str]]:

    cumulative_time = 0
    failed: list[str] = []
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=batch['max_workers']) as executor:
        futures = {executor.submit(look_at_file, fp, index+prior_processed): fp for index, fp in enumerate(batch['paths'])}
        for future in concurrent.futures.as_completed(futures):
            fp = futures[future]
            try:
                head, liths, blows, time_taken = future.result()
                if head and out_putter:
                    logger.info('in recognizable format')
                    for h in head:
                        out_putter.write_header(h, fp)
                    for b in blows:
                        out_putter.write_blow_file(b)
                    for l in liths:
                        out_putter.write_lithology_file(l)
                cumulative_time += time_taken
            except Exception:
                logger.error(f'Failed to process {fp}')
                failed.append(fp)
                logging.exception('message')

    return cumulative_time, failed

def test_file_till_error(path: str):

    test_batch: Ideal_Batch = {
        'max_workers': 1,
        'paths': [path]
    }
    times_tried = 0

    while True:
        new_time = handle_batch(test_batch, times_tried, None)
        times_tried += 1
        if new_time == 0:
            logger.info('Found fault, ending test')
            break

# def look_at_file(file_path: str, file_index: int, draw_visuals=False, visuals_folder='visuals', use_cache=False) -> tuple[list[Document_Agenda], int]:
def look_at_file(file_path: str,
                 file_index: int,
                #  ocr_cls_false: PaddleOCR,
                #  ocr_cls_true: PaddleOCR,
                 draw_visuals=False,
                 visuals_folder='visuals',
                 use_cache=False
                 ) -> tuple[list[Header_Sheet_Entry]|None, list[list[Lithology_Sheet_Entry]], list[list[Blowcount_Sheet_Entry]], int]:
    
    start_time = int(time.time())
    from paddleocr import PaddleOCR
    from paddleocr import PaddleOCR
    from detect_structure.helpers.table_structure.table_structure import Table_Structure
    from detect_structure.helpers.table_structure.table_structure_half import Table_Structure_Half
    from labeled_sets import bbs_137_rev_8_99, page_dict
    from xplorer_tools.fix_orientation import fix_orientation
    from xplorer_tools.get_image_from_page import get_image_from_page
    from line_detection.detect_lines import detect_lines
    from detect_structure.detect_structure import detect_structure
    from find_logs.find_log import find_bbs_137_rev_8_99_log_pages
    import log_config as log_config
    from header_analysis.simply_get_page_groups import get_page_nums, get_empty_page_builder, build_page_group

    log_config.setup(log_prefix=file_index, do_paddle=True)
    logger = logging.getLogger(__name__)
    logger.info('BoringXplorer logger initialized')

    header_sheets: list[Header_Sheet_Entry] = []
    lithology_sheets: list[list[Lithology_Sheet_Entry]] = []
    blow_sheets: list[list[Blowcount_Sheet_Entry]] = []

    ocr_cls_false = PaddleOCR(cls=False, lang='en', ocr_version='PP-OCRv4', use_gpu=False)
    ocr_cls_true = PaddleOCR(cls=True, lang='en', ocr_version='PP-OCRv4', use_gpu=False)

    logger.warning(f'Started new thread ({file_index}) for {file_path}')
    
    # Get a list of all the pages that have logs on them
    logger.info(f'Doing {file_path}')
    log_locations = find_bbs_137_rev_8_99_log_pages(file_path, ocr_cls_false)
    logger.info(f'Logs found: {log_locations}')

    if len(log_locations) == 0:
        logger.info('Skipping file, no log locations')
        end_time = int(time.time())
        return None, [], [], (end_time - start_time)

    # Go through each log and determine the document structure and prior data
    logger.info('Finding structure data')
    structure_dict: dict[int, Table_Structure_Half|Table_Structure] = {}
    image_dict: dict[int, tuple[np.ndarray, np.ndarray]] = {}  # Maybe a tad irresponsible, not cause of the memory leak though
    current_builder: Page_Group_Builder = get_empty_page_builder()
    for index, doc_page_num in enumerate(log_locations):
        logger.info(f'Looking at page {doc_page_num}')
        
        g_gray_image, g_color_image = get_image_from_page(file_path, doc_page_num)
        g_gray_image, g_color_image = fix_orientation(g_gray_image, g_color_image, assess_count=6)

        logger.info('Fixed orientation')

        gray_array = np.array(g_gray_image, dtype=np.uint8)
        color_array = np.array(g_color_image, dtype=np.uint8)

        horizontals, verticals = detect_lines(
            gray_array,
            color_array,
            draw_visuals=draw_visuals,
            use_cache=use_cache,
            path=file_path,
            page=doc_page_num)

        logger.info('Lines detected')

        structure: Table_Structure | Table_Structure_Half
        structure = detect_structure(horizontals,
                                     verticals,
                                     gray_array,
                                     color_array,
                                     use_cache=use_cache,
                                     path=file_path,
                                     page=doc_page_num,
                                     draw_visuals=draw_visuals)

        logger.info('Structure found')

        # Update dicts
        structure_dict[doc_page_num] = structure
        image_dict[doc_page_num] = gray_array, color_array

        # Now add the page to the document, build it one page at a time
        page_num, page_total = get_page_nums(ocr_cls_false, color_array, draw_visuals=draw_visuals, visuals_folder=visuals_folder)
        logger.info(f'Found page: {page_num} and page total: {page_total}')

        is_last_log = index == len(log_locations) - 1
        
        docs_to_build: list[list[int]]
        if is_last_log:
            logger.info('LAST LOG')
        docs_to_build, current_builder = build_page_group(current_builder, page_num, page_total, doc_page_num, is_last_log)

        # If we finished documents, handle them and then reset the dicts
        if len(docs_to_build) > 0:
            logger.info(f'Created groups: {docs_to_build}')
            for document in docs_to_build:
                part_header_sheets: list[Header_Sheet_Entry]
                part_lithology_sheets: list[list[Lithology_Sheet_Entry]]
                part_blow_sheets: list[list[Blowcount_Sheet_Entry]]

                part_header_sheets, part_lithology_sheets, part_blow_sheets = handle_actual_page_group(document,
                                                                                                       structure_dict,
                                                                                                       image_dict,
                                                                                                       ocr_cls_false,
                                                                                                       ocr_cls_true,
                                                                                                       file_index,
                                                                                                       draw_visuals=draw_visuals,
                                                                                                       visuals_folder=visuals_folder)
                header_sheets += part_header_sheets
                lithology_sheets += part_lithology_sheets
                blow_sheets += part_blow_sheets

                # Reset the cached stuff we have
                for doc_page in document:
                    del structure_dict[doc_page]
                    del image_dict[doc_page]
        # return header_sheets, lithology_sheets, blow_sheets, 1 # Added, remove after testing

    end_time = int(time.time())
    logger.info(f'Took {end_time - start_time} seconds')

    return header_sheets, lithology_sheets, blow_sheets, (end_time - start_time)
    

def handle_actual_page_group(log_locations: list[int],
                             structure_dict, # : dict[int, Table_Structure_Half | Table_Structure]
                             image_dict: dict[int, tuple[np.ndarray, np.ndarray]],
                             ocr_cls_false, # : PaddleOCR
                             ocr_cls_true, # : PaddleOCR
                             file_index: int,
                             draw_visuals=False,
                             visuals_folder='visuals'):

    from header_analysis.analyze_header import Header_Obj
    from header_analysis.analyze_waters import Water_Obj
    from detect_structure.helpers.find_BUM_info.blowcount import BlowCount
    from detect_structure.helpers.lithology_formation import Lithology_Formation
    from header_analysis.find_page_groups import find_page_groups
    from detect_structure.helpers.find_descriptions.find_descriptions import find_descriptions
    from detect_structure.helpers.find_BUM_info.find_blow_counts import find_blow_counts
    from document_agenda.document_agenda import Document_Agenda
    from xplorer_tools.fix_analysis_objects import take_majority_header, take_majority_water
    from detect_structure.helpers.table_structure.table_structure import Table_Structure
    from detect_structure.helpers.table_structure.table_structure_half import Table_Structure_Half


                             
    # page_groups: list[list[int]]
    header_dict: dict[int, Header_Obj]
    water_dict: dict[int, Water_Obj]
    header_dict, water_dict = find_page_groups(log_locations,
                                               structure_dict,
                                               image_dict,
                                               ocr_cls_false,
                                               draw_visuals=draw_visuals,
                                               visuals_folder=visuals_folder)

    # logger.info(f'Found page groups {page_groups}')

    # We can now go through and update the rulers on each structure
    logger.info('Finding rulers')
    for index, page_num in enumerate(log_locations):
        logger.info(f'Page {page_num}')

        left_ends  = (0.0 + 40.0 * index, 20.0 + 40.0 * index)
        right_ends = (20.0 + 40.0 * index, 40.0 + 40.0 * index)
        color_image = image_dict[page_num][1]
        gray_image  = image_dict[page_num][0]
        structure_dict[page_num].find_rulers(left_ends, right_ends, color_image, gray_image)

    # Now go through and find all the goodies (lithology and blow counts)
    logger.info('Resolving individual documents')
    all_agendas: list[Document_Agenda] = []

    logger.info('Looking for descriptions')
    description_list: list[Lithology_Formation] = []
    for index, page_num in enumerate(log_locations):
        color_image = image_dict[page_num][1]
        gray_image  = image_dict[page_num][0]
        page_structure = structure_dict[page_num]
        
        d1 = find_descriptions(color_image,
                                gray_image,
                                page_structure,
                                'l',
                                ocr_cls_false,
                                draw_visuals=draw_visuals,
                                visuals_folder=visuals_folder)
        description_list += d1
        logger.debug(f'Left side produced {d1}')

        if isinstance(page_structure, Table_Structure):
            d2 = find_descriptions(color_image,
                                    gray_image,
                                    page_structure,
                                    'r',
                                    ocr_cls_false,
                                    draw_visuals=draw_visuals,
                                    visuals_folder=visuals_folder)
            description_list += d2
            logger.debug(f'Right side produced {d2}')

    logger.info(f'Found {len(description_list)} Lithology sections before resolving continuations')
    
    # Combine descriptions together
    index = 1
    while index < len(description_list):

        if description_list[index].is_continuation:

            # Sometimes a block will be empty and/or just have some water symbol
            # in it. If that's the case AND it has a continuation after that,
            # hooray. We can update the description to something more meaningful
            if len(description_list[index-1].description) < 4:
                description_list[index].fix_being_continuation()
                description_list[index-1].description = description_list[index].description
            
            description_list[index-1].append_continuation(description_list[index])

            description_list.pop(index)
            continue

        index += 1

    logger.debug(f'Resulting lithology sections ({len(description_list)}) {description_list}')
    group_header = take_majority_header([header_dict[g] for g in log_locations])
    group_water = take_majority_water([water_dict[g] for g in log_locations])
    agenda = Document_Agenda(description_list, group_header, group_water, file_index)
    agenda.trim_lithology()

    logger.info('Looking for blow counts')
    blow_count_list: list[BlowCount] = []
    for index, page_num in enumerate(log_locations):

        color_image = image_dict[page_num][1]
        gray_image  = image_dict[page_num][0]
        page_structure = structure_dict[page_num]

        b1 = find_blow_counts(color_image,
                                gray_image,
                                page_structure,
                                'l',
                                agenda,
                                ocr_cls_true,
                                draw_visuals=draw_visuals,
                                visuals_folder=visuals_folder)
        blow_count_list += b1
        logger.debug(f'Left side produced {b1}')

        if isinstance(page_structure, Table_Structure):
            b2 = find_blow_counts(color_image,
                                    gray_image,
                                    page_structure,
                                    'r',
                                    agenda,
                                    ocr_cls_true,
                                    draw_visuals=draw_visuals,
                                    visuals_folder=visuals_folder)
            blow_count_list += b2
            logger.debug(f'Right side produced {b2}')

    logger.info(f'Found {len(blow_count_list)} Blow count sections before resolving continuations')

    blow_count_list.sort(key=lambda b:b.top_bound)

    # Combine incomplete blow counts
    index = 0
    while index < len(blow_count_list) - 1:

        if blow_count_list[index].incomplete and blow_count_list[index+1].incomplete:
            blow_count_list[index].append_continuation(blow_count_list[index+1])
            blow_count_list.pop(index+1)

        elif blow_count_list[index].incomplete and not blow_count_list[index+1].incomplete:
            logger.warning('Found two consecutive BUM sections where the prior was incomplete')
            logger.warning(f'Before combination {blow_count_list[index].blows} and {blow_count_list[index+1].blows}')
            blow_count_list[index].append_continuation(blow_count_list[index+1])
            blow_count_list.pop(index+1)
            logger.warning(f'After combination {blow_count_list[index].blows}')

        index += 1

    logger.debug(f'Resulting blow counts ({len(blow_count_list)}) {blow_count_list}')

    agenda.blow_counts = blow_count_list
    
    logger.info('Completed agenda')
    logger.debug('Resulting agenda:')
    logger.debug(agenda)


    all_agendas.append(agenda)

    header_sheets = [a.get_header_sheet_entry() for a in all_agendas]
    lithology_sheets = [a.get_lithology_sheet_entries() for a in all_agendas]
    blow_sheets = [a.get_blowcount_sheet_entries() for a in all_agendas]

    return header_sheets, lithology_sheets, blow_sheets