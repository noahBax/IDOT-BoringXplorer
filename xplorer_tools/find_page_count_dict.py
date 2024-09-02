def find_page_count_dict(file_paths: list[str]) -> dict[str, int]:
    import fitz

    ret: dict[str, int] = {}
    for path in file_paths:
        with fitz.open(path) as pdf:
            ret[path] = pdf.page_count

    return ret