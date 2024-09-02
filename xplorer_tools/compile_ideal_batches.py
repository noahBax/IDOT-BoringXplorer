import logging
from math import floor
from typing import TypedDict
import multiprocessing
from configparser import ConfigParser
import random

logger = logging.getLogger(__name__)

class Ideal_Batch(TypedDict):
    max_workers: int
    paths: list[str]

# Got it from geeksforgeeks
def give_me_batches(cookies: list[str], size: int):
    # Get it. Batch of cookies? You come up with a better name
    for i in range(0, len(cookies), size):
        yield cookies[i : size+i]

def make_batch(max_workers: int, paths: list[str]) -> Ideal_Batch:
    return {
        'max_workers': max_workers,
        'paths': paths
    }

def compile_ideal_batches(page_dict: dict[str, int], config: ConfigParser, max_pages_per_batch=80) -> list[Ideal_Batch]:
    """
    Multithreading is a way to speed up work, but PaddleOCR adds a lot of
    overhead to each process. Additionally, in order to get around the "memory
    leak" it has, we need to rest every so often to explicitly tell the garbage
    collector to do its job.

    So we pack things into batches. Each batch has
      1) A core limit which is the number of processes available
      2) A list of file paths

    Each batch of Noah's homemade computational cookies is crafted with the love
    and care that aims to constrain the max memory footprint. The secret's in
    the X27 fiber technology, making it over 27 times more efficient than just
    parsing all the god damn documents at once.

    Nah, jkjk I'm just capping exs dee. The memory leak comes about because old
    tensors aren't un-cached by PaddlePaddle, and if you let it run forever the
    OS kills it. A similarish thing seems to happen with PyMuPDF so I figure the
    best thing is to just limit the number of pages that are in each batch to
    solve the PyMuPDF issue AND limit the size of the files being analyzed and
    being passed through PaddleOCR so that multiple processes can run at once.
    
    The overall aim is to keep the total footprint under 10 GiB. This doesn't
    always happen and it usually sits at under 7 GiB, but it's infinitely better
    than letting it run it take up all 24 free gigs of my PC's memory and making
    me wonder why it's crashing.

    This is very much a "it ain't broke, don't fix it" solution. It is not
    elegant. Fix it.
    """

    # If put in low memory mode, want to limit the number of pages that are
    # loaded at max into memory. This can't really be helped for longer
    # documents, but it can at least be helped in general
    if config['BEHAVIOR']['LowMemoryMode'] == 'yes':
        max_pages_per_batch = floor(max_pages_per_batch/2)


    # If multithreading is enabled, assign the shorter documents to be used in
    # multiple cores and do longer documents with only one core
    longer_docs: list[str]

    if config['BEHAVIOR']['UseMultiThreading'] == 'yes' and config['BEHAVIOR']['LowMemoryMode'] != 'yes':

        cpu_count = multiprocessing.cpu_count()
        logger.info(f'CPU Core count is {cpu_count}')

        if cpu_count < 5:
            short_cores = 1
            med_cores = 1
        elif cpu_count < 7:
            short_cores = 2
            med_cores = 2
        elif cpu_count < 9:
            short_cores = 3
            med_cores = 2
        else:
            short_cores = 4
            med_cores = 2

        logger.info(f'Short tasks get {short_cores} cores')
        logger.info(f'Medium tasks get {med_cores} cores')
        
        short_docs = [d for d in page_dict if page_dict[d] == 1 or page_dict[d] == 2]
        med_docs = [d for d in page_dict if page_dict[d] == 3 or page_dict[d] == 4]
        longer_docs = [d for d in page_dict if page_dict[d] > 4]

        ret: list[Ideal_Batch] = []

        count_short = 0
        if len(short_docs) > 0:
            size = floor(max_pages_per_batch / 2)
            one_long_batch = list(give_me_batches(short_docs, size))
            for b in one_long_batch:
                ideal = make_batch(5, b)
                if len(ideal['paths']) > size/2:
                    ret.append(ideal)
                    count_short += 1
                else:
                    med_docs.extend(b)
                    random.shuffle(med_docs)


        count_med = 0
        if len(med_docs) > 0:
            size = floor(max_pages_per_batch / 4)
            two_long_batch = list(give_me_batches(med_docs, size))
            for b in two_long_batch:
                ideal = make_batch(3, b)
                if len(ideal['paths']) > size / 2:
                    ret.append(ideal)
                    count_med += 1
                else:
                    longer_docs.extend(b)
    
    else:
        longer_docs = list(page_dict.keys())

    # Take care of the remaining documents. Or all of them if multithreading is
    # enabled
    count_long = 0
    longer_docs.sort(key=lambda p: page_dict[p])
    while len(longer_docs) > 0:
        e = longer_docs.pop()
        total_pages = page_dict[e]

        new_batch_docs = [e]
        look_index = len(longer_docs) - 1
        
        while total_pages < max_pages_per_batch and look_index > -1:
            if page_dict[longer_docs[look_index]] + total_pages <= max_pages_per_batch:
                t = longer_docs.pop(look_index)
                new_batch_docs.append(t)
                total_pages += page_dict[t]
            
            look_index -= 1

        ret.append(make_batch(1, new_batch_docs))
        count_long += 1
    
    logger.info(f'Compiled {count_short} short batches')
    logger.info(f'Compiled {count_med} medium batches')
    logger.info(f'Compiled {count_long} long batches')

    return ret