class blowcount_information:
    """
    I'm not entirely sure what a blowcount is exactly. I think it has something
    to do with core samples given that each is 1'. Regardless, each entry has a
    top depth, bottom depth, sample type, lithology component description, a SPT
    value (N value), a UCS value (Qu), a Qu letter, and a moisture value. Not
    all of these fields are guaranteed to be filled in though.

    Generally speaking, a blowcount section is 1' in size and is defined by a
    top and bottom horizontal line stretching across the BUM columns. For some
    older formats, that line is broken up by a 3rd number (3rd number also
    appears in BBS 137 Rev. 8-99 format) (which doesn't appear to have any
    meaning) on the top and the 2nd number on the bottom.

    Inside of each section can be either 1 or 2 numbers. For our purposes, just
    sum the two numbers together and treat it as 1. I mentioned the 3rd number
    above and it doesn't seem to have any importance to what we're doing.

    The lithology component description comes from the lithology_formation's
    component_description that the top depth of the blowcount lies in.

    Some things not included:
    The engineering spreadsheet has QP and QU listed and I don't know what the
    difference between them is. I figure that they can be calculated trivially,
    so for now I'm just going to keep one number as UCS value.
    """