import logging
import csv
from datetime import datetime
from pathlib import Path
from document_agenda.output_information import *
from configparser import ConfigParser

logger = logging.getLogger(__name__)

class Output_Manager:


    def __init__(self, config: ConfigParser) -> None:
        
        try:

            if config['BEHAVIOR']['UseDateInOutputFileNames'] == 'yes':
                now = datetime.now()
                date_str = now.strftime("%m_%d_%Y_%H_%M_%S") + '_'
            else:
                date_str = ''

            header_name = f'{date_str}headers_tabulated.csv'
            blow_name = f'{date_str}blowcounts_tabulated.csv'
            lithology_name = f'{date_str}lithology_formations_tabulated.csv'
            
            self.header_file = open(header_name, 'w', newline='')
            self.blow_file = open(blow_name, 'w', newline='')
            self.lithology_file = open(lithology_name, 'w', newline='')
            self.success = True
        except PermissionError:
            logger.critical('Could not interact with one of the csv files. Make sure that it is not open elsewhere')
            self.success = False
            return

        self.header_writer = csv.DictWriter(self.header_file, fieldnames=FULL_HEADER_LIST)
        self.blow_writer = csv.DictWriter(self.blow_file, fieldnames=FULL_BLOWCOUNT_LIST)
        self.lithology_writer = csv.DictWriter(self.lithology_file, fieldnames=FULL_LITHOLOGY_LIST)

        self.header_writer.writeheader()
        self.blow_writer.writeheader()
        self.lithology_writer.writeheader()

    def write_header(self, header_obj: Header_Sheet_Entry, file_path: str) -> None:
        header_obj['FILE_PATH'] = file_path
        self.header_writer.writerow(header_obj)

    def write_blow_file(self, blow_list: list[Blowcount_Sheet_Entry]) -> None:
        self.blow_writer.writerows(blow_list)

    def write_lithology_file(self, lith_list: list[Lithology_Sheet_Entry]) -> None:
        self.lithology_writer.writerows(lith_list)
    
    @staticmethod
    def _check_csv_exists(fname: str, fields_default: list[str]) -> None:
        does_exist = Path(fname)
        if not does_exist:
            with open(fname, 'w') as f:
                f.write(','.join(fields_default))