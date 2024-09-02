from __future__ import annotations
from detect_structure.helpers.find_BUM_info.BUM_pair import Pair
# from document_agenda.document_agenda import Document_Agenda

# In the future, maybe we can pass this a list of all of the descriptions and
# have it ask the corresponding descriptions for a summary of an attribute at
# this blowcount?

class BlowCount:

    def __init__(self, pair: Pair, blow_counts: list[int], document_agenda) -> None:

        self.top_bound = pair.top_bound
        self.low_bound = pair.low_bound
        self.blows = sum(blow_counts)

        self.blow_count_sections = blow_counts

        self.incomplete = pair.incomplete

        if pair.top_pair:
            self.position = 'top'
        elif pair.bottom_pair:
            self.position = 'bottom'
        else:
            self.position = 'middle'

        self.description = document_agenda.soil_magnify(self.top_bound)

        # There should only be one 'last' in a series of blow counts
        self.last_BUM = False

    def append_continuation(self, new_blow: BlowCount):

        # Check to see if this is a valid operation
        if not self.incomplete:
            raise Exception('Tried to append to a continuation that was already complete')

        if len(self.blow_count_sections) > 1:
            raise Exception('Tried to append to a continuation that already had enough blows')

        # It it didn't have any recognizable numbers in it, disregard it
        if len(new_blow.blow_count_sections) == 0:
            return
        
        self.blows = self.blows + new_blow.blow_count_sections[0]

        # See "Morgan County/069-0506 SOIL 2000.pdf" page 11 for some good
        # examples of this, but the algorithm for determining BUM boundaries
        # works by surveying each of the blows, ucs, and moisture columns for
        # line markers and then records a boundary where at least 2 of 3 agree.
        # That works most of the time, except for in that case where the UCS
        # column extends down a bit. The boundary itself does not extend that
        # far and it should only have a max of two measurements in it
        lose_this_ground = len(new_blow.blow_count_sections) - 1
        
        self.low_bound = new_blow.low_bound - lose_this_ground*0.5
        self.incomplete = False

    
    def __str__(self) -> str:
        s = f'{self.top_bound} : {self.description} : {self.low_bound} -> {self.blows}'

        if self.incomplete:
            s += ' || incomplete'

        return s

    def __repr__(self) -> str:
        return self.__str__()