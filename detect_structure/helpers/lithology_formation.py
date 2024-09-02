from __future__ import annotations
import logging
from math import floor
import re

logger = logging.getLogger(__name__)

class Lithology_Formation:
    """
    Lithology formations are sections on the lithology scale. They each have a
    description, a component description, a start depth, and an end depth. They
    can also have an array of modifiers which have a description and an
    associated depth.

    The easiest way to spot the difference between lithology formations is by
    looking for a horizontal line on the lithology scale. This isn't always the
    case though. If a lithology formation has a description that is too long and
    doesn't fit between the description of the layer above and below it, it will
    just go down however far it needs and a horizontal line will be placed
    partially underneath it and a diagonal line will connect it to where it's
    supposed to be on the ruler.

    From what I can gather, a section change happens when the text written at a
    point on the lithology scale mentions a different material written in
    CAPITAL letters appears. E.g. "Grey medium grained clean sandy gravel" to
    "Grey fine grained clean sand" where SANDY GRAVEL and SAND were capitalized.

    Given that OCR isn't the most consistent thing, I think it's probably better
    not to look for capitalization and to just look for descriptions like sand,
    clay, silt, etc. If it's too hard doing that, I'll switch to capitalization.

    The modifiers are for smaller things that happen inside a lithographic
    section. E.g. a modifier might say "Medium grained" which doesn't really
    signify a switch, but it is an important note.
    """

    def __init__(self, description: str, top: float, bottom: float) -> None:
        
        if top > bottom:
            logger.critical(f'description: {description}')
            logger.critical(f'top: {top}')
            logger.critical(f'bottom: {bottom}')
            raise Exception('Top depth cannot be lower than bottom depth')

        self.description = Lithology_Formation._fix_mistakes(description)
        self.top = top
        self.bottom = bottom
        self.modifiers: list[tuple[str, float]] = []

        self.is_continuation = not not re.search(r'[co][o0]n[tf][il1]?n[uvy]ed', description, re.IGNORECASE)


    def add_modifier(self, description: str, depth: float) -> None:

        if depth > self.bottom or depth < self.top:
            logger.critical(f'description: {self.description}')
            logger.critical(f'modifier: {description}')
            logger.critical(f'depth: {depth}')
            raise Exception('Tried to add modifier that was outside of formation')

        desc = Lithology_Formation._fix_mistakes(description)

        # If there is a "w/" at the beginning, remove it
        desc = re.sub(r'^w[//|]', '', desc, flags=re.IGNORECASE)
        
        self.modifiers.append((desc, depth))

    def append_continuation(self, lithology: Lithology_Formation) -> None:
        logger.debug(f'There are {len(lithology.modifiers)} to append')

        # Extend the range first
        self.bottom = lithology.bottom

        # Append the modifiers
        self.modifiers = self.modifiers + lithology.modifiers

    def build_output_string(self) -> str:
        out = self.description
        for m in self.modifiers:
            out += f'; {m[0]} @{m[1]}'

        # Replace these weird mistakes
        out = re.sub(r'\([li1][li1]\)', '(Till)', out, flags=re.IGNORECASE)
            
        return out
        
    def check_if_end(self) -> tuple[Lithology_Formation, bool] | None:
        completion_sig = re.compile(r'[b8][o0]r[ij]n[g9]\s*C[o0](rn|m)p[l1i]eted?', re.IGNORECASE)
        refusal_sig = re.compile(r'au[g9]er refu[s$]a[1i]', re.IGNORECASE)
        abandoned_sig = re.compile(r'aband[o0]ned? h[o0][l1i]e', re.IGNORECASE)
        refer_sig = re.compile(r'refer ([s$][t]a[t][l1i][o0]n|[s$][t]a|e[l1i]eva[t]?[l1i]?[o0]n)', re.IGNORECASE)

        # 'Boring Completed' and 'Abandoned Hole' are keys to throw out the
        # whole block. They *usually* appear first.
        if re.search(completion_sig, self.description) or re.search(abandoned_sig, self.description):
            return None

        for mod in self.modifiers:
            if re.search(completion_sig, mod[0]) or re.search(abandoned_sig, mod[0]):
                return None

        # I think if we see 'Auger Refusal' it means drop this entry and any
        # entries after it if it's in a modifier

        # As a side note, dropping everything after an auger refusal can get rid
        # of some information that gets recorded from a rock core log, but those
        # are really inconsistent
        if re.search(refusal_sig, self.description):
            return None
        
        for index, mod in enumerate(self.modifiers):
            if re.search(refusal_sig, mod[0]):
                self.modifiers = self.modifiers[:index]
                return self, True

        # The 'refer station/sta/elevation to' doesn't seem the most consistent
        # and I cannot tell exactly what it means, but it is always at the end
        # of a document if it is there. Unique case in particular is 'Menard
        # County/065-3007 SOIL 2001.pdf' page 5.
        if re.search(refer_sig, self.description):
            return None
        
        for mod in self.modifiers:
            if re.search(refer_sig, mod[0]):
                return None

        # Of course, if there are no matches, just return yourself
        return self, False

    def fix_being_continuation(self) -> None:
        # Just replace the description with an altered version
        self.description = re.sub(r'\(?[co][o0]n[tf][il1]?n[uvy]ed\)?', '', self.description, flags=re.IGNORECASE)
        

    def __str__(self) -> str:
        return f"Lithology :: " \
               f"Spans {self.top}:{self.bottom}, " \
               f"is_continuation: {self.is_continuation}, " \
               f"Description: {self.description}, " \
               f"Modifiers: {self.modifiers}"

    def __repr__(self) -> str:
        return self.__str__()

    # Yeah I know these aren't a great way to do this, but they are mistakes
    # that annoyed me during testing
    @staticmethod
    def _fix_mistakes(s: str):
        s = s.replace('$', 'S')
        for mistake, repl in Lithology_Formation.stupid_mistakes:
            s = re.sub(mistake, repl, s)
        s = re.sub(r'^[.,:; ]+', '', s)
        return s

    stupid_mistakes: list[tuple[re.Pattern, str]] = [
        (re.compile(r'[({][t1]?[li1][li1][)}]l?', re.IGNORECASE), '(Till)'),  # (ll), (Til)
        (re.compile(r'[({][t1][li1][)}]', re.IGNORECASE), '(Till)'),  # (Tl)
        (re.compile(r"we[tf]'[s$][il1][li1][tf]", re.IGNORECASE), 'Wet SILT'),  # Wet'SILT
        (re.compile(r'[({]f[il1!][li1m][)}]', re.IGNORECASE), '(Fill)'), # (Fil), (FiM)
        (re.compile(r'[({]F[il1!]D[)}]'), '(Fill)'), # (FiD)
        (re.compile(r'[({]Til(?![li1])(?![)}])\s'), '(Till)'), # (Til
        (re.compile(r'LQAM'), 'LOAM'), # LQAM
        (re.compile(r'[({][t1][li1][ft][)}]', re.IGNORECASE), '(Till)'), # (Tif), (TiT)
        (re.compile(r'[({][t1][il1][li1][li1][li1][)}]', re.IGNORECASE), '(Till)'), # (Tilll)
        (re.compile(r'3rown'), 'Brown'),
        (re.compile(r'SlLT'), 'SILT'),
        (re.compile(r'[ft]i[s$][s$][li1]e', re.IGNORECASE), 'Fissile'),
        (re.compile(r'_[o0]am', re.IGNORECASE), 'LOAM'),  # _OAM
        (re.compile(r'[\.,]+$'), '.'),  # '...' at the end of strings
        (re.compile(r'[s$][il1]L$|[s$][il1]L\s+', re.IGNORECASE), 'SILT'), # SIL
        (re.compile(r'[s$][il1][li1][tf][yv]', re.IGNORECASE), 'SILTY'),  # SILFY as well as other, non-uppercase silty's
        (re.compile(r'\s+F[il1]\)'), ' (Fill)'),  # CLAY Fl)
        (re.compile(r'[({][t1][il1][li1][li1](?![)}li1])', re.IGNORECASE), '(Till)'),  # ClAY (Till
        (re.compile(r'[({]f[il1][li1]d[)}]', re.IGNORECASE), '(Fill)'),  # (FilD)
        (re.compile(r'[({]f[il1]m[li1][)}]', re.IGNORECASE), '(Fill)'),  # (FilD)
        (re.compile(r'[({]T[il1!n]{3}[)}]'), '(Till)'),  # General (Till)
        (re.compile(r'[({]Tm[il1!n]{2}[)}]'), '(Till)'),  # (Tmll)
        (re.compile(r'\s+F[il1!]{3}[)}]'), ' (Fill)'),  # LOAM Fill)
        (re.compile(r'\s+T[il1!]{3}[)}]'), ' (Till)'),  # LOAM Till)'
        (re.compile(r'(?<=l)1(?=me)', re.IGNORECASE), 'I'),  # L1MESTONE
        (re.compile(r'sil7', re.IGNORECASE), 'SILT'),  # SIL7
        (re.compile(r'sjlt', re.IGNORECASE), 'SILT'),  # SjLTY
        (re.compile(r'\s+w!\s+'), 'w/'),
        (re.compile(r'LOA[VN]\s'), 'LOAM '),  # LOAV, LOAN
        (re.compile(r'\stc\s'), ' to '),  # silt tc clay
    ]