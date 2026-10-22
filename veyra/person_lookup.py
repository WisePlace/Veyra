from urllib.parse import quote, quote_plus


def _q(s):
    return quote(s)


def _qp(s):
    return quote_plus(s)


def build(first, last, keyword=""):
    first = (first or "").strip()
    last = (last or "").strip()
    keyword = (keyword or "").strip()
    full = " ".join(p for p in (first, last) if p).strip()
    if not full:
        return {"ok": False, "error": "Enter at least a first or last name."}

    phrase = f'"{full}"'
    extra = f" {keyword}" if keyword else ""
    q_web = _qp(phrase + extra)
    q_plain = _qp(full + extra)
    q_name = _qp(full)

    groups = [
        {"name": "Search engines", "links": [
            {"label": "Google", "url": f"https://www.google.com/search?q={q_web}"},
            {"label": "Bing", "url": f"https://www.bing.com/search?q={q_web}"},
            {"label": "DuckDuckGo", "url": f"https://duckduckgo.com/?q={q_web}"},
            {"label": "Yandex", "url": f"https://yandex.com/search/?text={q_web}"},
            {"label": "Google Images", "url": f"https://www.google.com/search?tbm=isch&q={q_web}"},
        ]},
        {"name": "Google dorks", "links": [
            {"label": "LinkedIn profiles", "url": f"https://www.google.com/search?q={_qp('site:linkedin.com/in ' + phrase + extra)}"},
            {"label": "Facebook", "url": f"https://www.google.com/search?q={_qp('site:facebook.com ' + phrase + extra)}"},
            {"label": "X / Twitter", "url": f"https://www.google.com/search?q={_qp('(site:twitter.com OR site:x.com) ' + phrase)}"},
            {"label": "Instagram", "url": f"https://www.google.com/search?q={_qp('site:instagram.com ' + phrase)}"},
            {"label": "Documents (PDF/DOC)", "url": f"https://www.google.com/search?q={_qp(phrase + extra + ' (filetype:pdf OR filetype:doc OR filetype:docx)')}"},
            {"label": "CV / Resume", "url": f"https://www.google.com/search?q={_qp(phrase + ' (CV OR resume OR curriculum)')}"},
        ]},
        {"name": "Social networks", "links": [
            {"label": "LinkedIn people", "url": f"https://www.linkedin.com/search/results/people/?keywords={q_name}"},
            {"label": "Facebook people", "url": f"https://www.facebook.com/search/people/?q={q_name}"},
            {"label": "X / Twitter users", "url": f"https://x.com/search?q={q_name}&f=user"},
            {"label": "Instagram", "url": f"https://www.instagram.com/explore/search/keyword/?q={q_name}"},
            {"label": "TikTok users", "url": f"https://www.tiktok.com/search/user?q={q_name}"},
            {"label": "GitHub users", "url": f"https://github.com/search?q={q_name}&type=users"},
            {"label": "YouTube", "url": f"https://www.youtube.com/results?search_query={q_name}"},
        ]},
        {"name": "People search", "links": [
            {"label": "Pages Blanches (FR)", "url": f"https://www.pagesjaunes.fr/pagesblanches/recherche?quoiqui={q_name}"},
            {"label": "ThatsThem", "url": f"https://thatsthem.com/name/{_q(first)}-{_q(last)}" if first and last else f"https://thatsthem.com/search?q={q_name}"},
            {"label": "TruePeopleSearch (US)", "url": f"https://www.truepeoplesearch.com/results?name={q_name}"},
            {"label": "FastPeopleSearch (US)", "url": f"https://www.fastpeoplesearch.com/name/{_q(first)}-{_q(last)}" if first and last else f"https://www.fastpeoplesearch.com/"},
            {"label": "WebMii", "url": f"https://webmii.com/people?n={q_name}"},
        ]},
    ]

    return {"ok": True, "name": full, "keyword": keyword, "groups": groups}
