import re

MISTAKES: dict[str, re.Pattern[str]] = {
    'route': re.compile(r'r?[o0]u[tf]e', flags=re.IGNORECASE),
    'description': re.compile(r'de[s$]cr[il1!]pt[il1!][o0]n', flags=re.IGNORECASE),
    'logged by': re.compile(r'l.?[o0].?g+.?e.?d? ?[b8s].?[yvu]?', flags=re.IGNORECASE),
    'section': re.compile(r'[s$]ect[il1!][o0]n', re.IGNORECASE),
    'location': re.compile(r'l.?[o0].?c.?a.?t.?[il1!].?[o0].?n', re.IGNORECASE),
    'county': re.compile(r'[co][o0]un+t[yvu]', re.IGNORECASE),
    'drilling method': re.compile(r'dr[il1!t][li1t!][li1t][il1!]ng[\s\.,]*[mn].?eth[o0]d', re.IGNORECASE),
    'hammer type': re.compile(r'[hmn]ammer\s*t[yvu]p+e', re.IGNORECASE),
    'struct no': re.compile(r'[s$]truct[,.:]?[\s\.,]*n[o0][,.:]?', re.IGNORECASE),
    'station': re.compile(r'[s$][tf]a[tf][il1!][o0]n', re.IGNORECASE),
    'boring no': re.compile(r'[b8s][o0]r[il1!]ng[\s\.,:]*n[o0]\.?', re.IGNORECASE),
    'offset': re.compile(r'[o$][ft][ft][s$]e[tf]', re.IGNORECASE),
    'ground surface elev': re.compile(r'gr[o0]u..?d[\s\.,]*[s$]ur[ft]ace[\s\.,]*e[li1t]e[vyu][.,]?', re.IGNORECASE),
    'date': re.compile(r'd[ao][tf]e?:?', re.IGNORECASE),
    'page': re.compile(r'page:?', re.IGNORECASE),
    'surface water elev': re.compile(r'[s$]ur.a[co]e[\s\.,]*wa[tf]er[\s\.,]*e[li1t]e[vyu][.,]?', re.IGNORECASE),
    'stream bed elev': re.compile(r'[s$][tf]rea(m|rn|n)[\s\.,]*[b8s]ed[\s\.,]*e[li1t]e[vyu][.,]?', re.IGNORECASE),
    'first encounter': re.compile(r'f[il1]r[s$][tf][\s\.,]*enc[o0][uvy]n[tf]er', re.IGNORECASE),
    'upon completion': re.compile(r'[uvyj]?p[o0]n[\s\.,]*[co0][o0].p[li1t]e[tf][i1l!][o0]n', re.IGNORECASE),
    'after hrs': re.compile(r'a[ft]er', re.IGNORECASE)
}

# ocr_anal_pairs =  PaddleOCR(cls=True, lang='en', ocr_version='PP-OCRv4')

# ocr_text_blobs =  PaddleOCR(cls=False, lang='en', ocr_version='PP-OCRv4')
# ocr_bbs_texts =   PaddleOCR(cls=False, lang='en', ocr_version='PP-OCRv4')
# ocr_page_groups = PaddleOCR(cls=False, lang='en', ocr_version='PP-OCRv4')
# ocr_water_info =  PaddleOCR(cls=False, lang='en', ocr_version='PP-OCRv4')
# ocr_header_info = PaddleOCR(cls=False, lang='en', ocr_version='PP-OCRv4')