import logging
import re
from detect_structure.helpers.lithology_formation import Lithology_Formation
from detect_structure.helpers.find_BUM_info.blowcount import BlowCount
from header_analysis.analyze_header import Header_Obj
from header_analysis.analyze_waters import Water_Obj
from document_agenda.output_information import *

logger = logging.getLogger(__name__)


class Document_Agenda:

    def __init__(self, description_list: list[Lithology_Formation], header: Header_Obj, water: Water_Obj, api_prefix: int) -> None:

        self.description_index = description_list
        self.blow_counts: list[BlowCount] = []
        self.api_number = f'{api_prefix}_{Document_Agenda.get_new_id()}'
        self.header_obj = header
        self.water_obj = water


    def soil_magnify(self, depth: float) -> str:
        """
        Look at the list of descriptions and get the attribute (or main
        description) at that depth
        """

        def update_description(desc: str, current: str):
            t = Document_Agenda.__get_component_description(desc)
            return t if t != '' else current

        # Loop through the description index until we find the lithology section
        # containing the depth
        logger.debug(depth)
        for formation in self.description_index:
            
            # Is it in this Lithology_Formation?
            if formation.top <= depth and formation.bottom > depth:
                section_description = update_description(formation.description, '')

                current_description = section_description
                for modifier in sorted(formation.modifiers, key=lambda m: m[1]):

                    if modifier[1] <= depth:
                        # Update the current description as we go down
                        current_description = update_description(modifier[0], current_description)

                        if modifier[1] == depth:
                            logger.debug(f'Returning {current_description}')
                            return current_description

                    elif modifier[1] > depth:
                        logger.debug(f'Returning {current_description}')
                        return current_description
                
                logger.debug(f'Returning {section_description}')
                return section_description

        # Just need to get the very last description we have
        last_formation = self.description_index[-1]

        if len(last_formation.modifiers) > 0:
            last_modifier = last_formation.modifiers[-1]
            return last_modifier[0]
            
        else:
            return last_formation.description

    def trim_lithology(self):
        # Walk along lithology list until you find the last one and remove
        # appropriate elements

        for index, lith in enumerate(self.description_index):
            end = lith.check_if_end()

            if end != None:
                new_lith, is_end = end

                # If it was the end but was just modified, alter the existing
                # index and then trim
                if is_end:
                    self.description_index[index] = new_lith
                    self.description_index = self.description_index[:(index+1)]
                    return
                    
            # If it was the end, trim everything 
            else:
                self.description_index = self.description_index[:index]
                return

    _agenda_id = 0

    @staticmethod
    def get_new_id() -> int:
        Document_Agenda._agenda_id += 1
        return Document_Agenda._agenda_id

    def __str__(self) -> str:
        ret: str
        ret = 'Description:\n' \
              f'{self.description_index}\n' \
              'Blow counts:\n' \
              f'{self.blow_counts}'
        return ret


    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def __get_component_description(raw_description: str) -> str:
        """
        I chose to simplify this from the original code I wrote (commented). To
        create a better summary like is done in the existing records is too
        complicated and leaves out too much information.
        """
        
        t = re.sub(r'\(?washed\)?', '', raw_description, flags=re.IGNORECASE)
        t = t.strip()

        return t

    def get_header_sheet_entry(self) -> Header_Sheet_Entry:
        ret: Header_Sheet_Entry = {
            'FILE_PATH': '',
            'API': self.api_number,
            'FARM_NAME': self.header_obj['description'],
            'Address': self.header_obj['route'],
            'COMPANY_NAME': 'IDOT',
            'TYPE': 'ENG',
            'COMP_DATE': self.header_obj['date_str'],
            'FARM_NUM': self.header_obj['boring_no'],
            'COUNTY': self.header_obj['county'],
            'COUNTY_CODE': county_code_dict[self.header_obj['county']] if self.header_obj['county'] != '' else -1,
            'SEC': self.header_obj['location_obj']['sec'],
            'TWP': self.header_obj['location_obj']['twp'],
            'TDIR': self.header_obj['location_obj']['tdir'],
            'RNG': self.header_obj['location_obj']['rng'],
            'RDIR': self.header_obj['location_obj']['rdir'],
            'MERIDIAN': self.header_obj['location_obj']['meridian'],
            'QUARTERS': self.header_obj['location_obj']['quarters'],
            'Elevation': self.header_obj['ground_surface_elev'],
            'SurfaceWaterElev': self.water_obj['surface_water_elv'],
            'GroundwaterElev1stEncounter': self.water_obj['first_encounter'],
            'GroundWaterElevCompletion': self.water_obj['upon_completion'],
            'GroundWaterElevAfterHours': self.water_obj['state_after_hours'],
            'Hours': self.water_obj['hours_till_state'],
            'Station': self.header_obj['boring_station'],
            'Offset': self.header_obj['offset']
        }
        return ret

    def get_lithology_sheet_entries(self) -> list[Lithology_Sheet_Entry]:
        ret: list[Lithology_Sheet_Entry] = [
            {
                'API': self.api_number,
                'FARM_NAME': self.header_obj['description'],
                'FARM_NUM': self.header_obj['boring_no'],
                'HBFORMATION_TOP': lith.top,
                'HBFORMATION_BOTTOM': lith.bottom,
                'HBFORMATION': lith.build_output_string()
            }
            for lith in self.description_index
        ]
        return ret

    def get_blowcount_sheet_entries(self) -> list[Blowcount_Sheet_Entry]:
        ret: list[Blowcount_Sheet_Entry] = [
            {
                'API': self.api_number,
                'FARM_NAME': self.header_obj['description'],
                'FARM_NUM': self.header_obj['boring_no'],
                'HB_Sample_Number': index+1,
                'HB_Sample_TOP': blow.top_bound,
                'HB_Sample_BOT': blow.low_bound,
                'HB_Lithology': blow.description,
                'N': blow.blows
            }
            for index, blow in enumerate(self.blow_counts)
        ]
        return ret