from xplorer_tools.types import ocr_analysis, ocr_coords

def average_y_of_ocr_coords(coords: ocr_coords) -> float:
    s = sum([c[1] for c in coords])
    return s/4

def top_of_ocr_coords(coords: ocr_coords) -> float:
    t: float = min([c[1] for c in coords])
    return t

def bottom_of_ocr_coords(coords: ocr_coords) -> float:
    b: float = max([c[1] for c in coords])
    return b

def left_of_ocr_coords(coords: ocr_coords) -> float:
    b: float = min([c[0] for c in coords])
    return b

def right_of_ocr_coords(coords: ocr_coords) -> float:
    b: float = max([c[0] for c in coords])
    return b

def average_of_top_ocr_coords(coords: ocr_coords) -> float:
    t = (coords[0][1] + coords[1][1]) / 2
    return t

def average_of_bottom_ocr_coords(coords: ocr_coords) -> float:
    t = (coords[2][1] + coords[3][1]) / 2
    return t

def height_span_ocr_coords(coords: ocr_coords) ->  float:
    top = min(coords[0][1], coords[1][1])
    low = max(coords[2][1], coords[3][1])
    return low - top

def center_ocr_coords(coords: ocr_coords) -> tuple[float, float]:
    avg_x = sum([c[0] for c in coords]) / 4
    avg_y = sum([c[1] for c in coords]) / 4
    return (avg_x, avg_y)

def join_horizontal_blocks(results: list[ocr_analysis], vertical_threshold=40.0, lateral_threshold=40.0) -> list[ocr_analysis]:
    """
    Join blocks as they flow from left to right
    """

    # Sort by left bounds
    blocks = sorted(results, key=lambda r: left_of_ocr_coords(r['coords_group']))

    # Join two if the centers are within threshold of each other AND are have
    # edges within threshold
    index = 0
    while index < len(blocks) - 1:
        curr = blocks[index]
        next = blocks[index+1]

        a = average_y_of_ocr_coords(curr['coords_group'])
        b = average_y_of_ocr_coords(next['coords_group'])

        c = right_of_ocr_coords(curr['coords_group'])
        d = left_of_ocr_coords(next['coords_group'])
        
        if abs(a - b) < vertical_threshold and abs(c - d) < lateral_threshold:
            # Combine them
            x1 = left_of_ocr_coords(curr['coords_group'])
            y1 = min(top_of_ocr_coords(curr['coords_group']), top_of_ocr_coords(next['coords_group']))

            x2 = max(right_of_ocr_coords(curr['coords_group']), right_of_ocr_coords(next['coords_group']))
            y2 = max(bottom_of_ocr_coords(curr['coords_group']), bottom_of_ocr_coords(next['coords_group']))

            new_coords: ocr_coords = ((x1, y1), (x2, y1), (x2, y2), (x1, y2))
            new_text = curr['text'] + ' ' + next['text']
            new_conf = min(curr['confidence'], next['confidence'])
            
            new_group: ocr_analysis = {
                'coords_group': new_coords,
                'confidence': new_conf,
                'text': new_text,
                'page_offset': curr['page_offset']
            }
            
            blocks.pop(index)
            blocks.pop(index)

            blocks.append(new_group)

            blocks.sort(key=lambda r: left_of_ocr_coords(r['coords_group']))

            index = 0
        else:
            index += 1

    return blocks

def join_vertical_blocks(results: list[ocr_analysis], threshold=40.0) -> list[ocr_analysis]:
    """
    Join blocks as they flow from top to bottom
    """

    # Sort by top
    blocks = sorted(results, key=lambda r: top_of_ocr_coords(r['coords_group']))

    # Join two if the top and bottom edges are within threshold
    index = 0
    while index < len(blocks) - 1:
        curr = blocks[index]
        next = blocks[index+1]

        a = bottom_of_ocr_coords(curr['coords_group'])
        b = top_of_ocr_coords(next['coords_group'])
        
        if abs(a - b) < threshold:
            # Combine them
            x1 = min(left_of_ocr_coords(curr['coords_group']), left_of_ocr_coords(next['coords_group']))
            y1 = top_of_ocr_coords(curr['coords_group'])

            x2 = max(right_of_ocr_coords(curr['coords_group']), right_of_ocr_coords(next['coords_group']))
            y2 = max(bottom_of_ocr_coords(curr['coords_group']), bottom_of_ocr_coords(next['coords_group']))

            new_coords: ocr_coords = ((x1, y1), (x2, y1), (x2, y2), (x1, y2))
            new_text = curr['text'] + ' ' + next['text']
            new_conf = min(curr['confidence'], next['confidence'])
            
            new_group: ocr_analysis = {
                'coords_group': new_coords,
                'confidence': new_conf,
                'text': new_text,
                'page_offset': curr['page_offset']
            }
            
            # Remove the ones we are combining
            blocks.pop(index)
            blocks.pop(index)

            blocks.append(new_group)

            # Sort the list and restart
            blocks.sort(key=lambda r: top_of_ocr_coords(r['coords_group']))
            index = 0
        else:
            index += 1

    return blocks