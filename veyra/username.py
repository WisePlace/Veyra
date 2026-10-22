import os
import re
import json
import concurrent.futures
import requests
from urllib.parse import urlparse

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "sites.json")
with open(_DATA_PATH, encoding="utf-8") as f:
    _RAW_SITES = json.load(f)

_VALID = re.compile(r"^[A-Za-z0-9._-]{1,40}$")


def _dom(url):
    try:
        n = urlparse(url).netloc.lower()
        return n[4:] if n.startswith("www.") else n
    except Exception:
        return url


def _base(url):
    parts = _dom(url).split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else _dom(url)


OVERRIDES = [
    {"name": "YouTube", "cat": "video",
     "check_url": "https://www.youtube.com/@{u}", "link_url": "https://www.youtube.com/@{u}",
     "method": "status", "not_found": [404], "conf": "high",
     "wall": ["consent.google", "consent.youtube", "Before you continue"], "source": "veyra"},
    {"name": "TikTok", "cat": "social", "method": "custom", "handler": "tiktok",
     "check_url": "https://www.tiktok.com/@{u}", "link_url": "https://www.tiktok.com/@{u}",
     "source": "veyra"},
    {"name": "Twitch", "cat": "gaming", "method": "custom", "handler": "twitch",
     "check_url": "https://www.twitch.tv/{u}", "link_url": "https://www.twitch.tv/{u}",
     "source": "veyra"},
    {"name": "X (Twitter)", "cat": "social", "method": "custom", "handler": "twitter",
     "check_url": "https://x.com/{u}", "link_url": "https://x.com/{u}",
     "source": "veyra"},
    {"name": "GitHub", "cat": "coding",
     "check_url": "https://github.com/{u}", "link_url": "https://github.com/{u}",
     "method": "status", "not_found": [404], "conf": "high", "source": "veyra"},
]

_override_bases = {_base(o["check_url"]) for o in OVERRIDES} | {"twitter.com", "facebook.com"}
_override_names = {o["name"].lower() for o in OVERRIDES} | {"facebook"}
ALL_SITES = OVERRIDES + [s for s in _RAW_SITES
                         if _base(s["check_url"]) not in _override_bases
                         and (s["name"] or "").lower() not in _override_names]


SIMPLE_DOMAINS = {
    "github.com", "gitlab.com", "bitbucket.org", "replit.com", "pypi.org",
    "npmjs.com", "hub.docker.com", "codepen.io", "keybase.io", "kaggle.com",
    "steamcommunity.com", "twitch.tv", "chess.com", "lichess.org", "roblox.com",
    "soundcloud.com", "spotify.com", "deviantart.com", "behance.net",
    "dribbble.com", "flickr.com", "vimeo.com", "last.fm", "medium.com",
    "patreon.com", "t.me", "about.me", "linktr.ee", "gravatar.com",
    "pinterest.com", "imgur.com", "trello.com", "producthunt.com", "reddit.com",
    "tiktok.com", "youtube.com", "instagram.com", "facebook.com", "tumblr.com",
    "snapchat.com", "wordpress.com", "telegram.me", "ko-fi.com",
    "buymeacoffee.com", "fandom.com", "slideshare.net", "goodreads.com",
}

SIMPLE_SITES = ([s for s in ALL_SITES if s.get("source") == "veyra"] +
                [s for s in ALL_SITES if s.get("source") != "veyra"
                 and _dom(s["check_url"]) in SIMPLE_DOMAINS])


def valid_username(u):
    return bool(_VALID.match(u or ""))


def sites_for(mode):
    return SIMPLE_SITES if mode == "simple" else ALL_SITES


def _evaluate(site, status, text):
    ec, es = site.get("pos_code"), site.get("pos_str")
    mc, ms = site.get("neg_code"), site.get("neg_str")

    exists = True
    if ec is not None:
        exists = exists and (status == ec)
    if es:
        exists = exists and (es in text)

    missing = False
    if mc is not None and status == mc:
        missing = True
    if ms and ms in text:
        missing = True

    if exists and not missing:
        signals = (1 if ec is not None else 0) + (1 if es else 0)
        return "found", "high" if signals >= 2 else "medium"
    return "absent", None


_CONSENT = {"CONSENT": "YES+1", "SOCS": "CAI"}


def _status_eval(site, r):
    if site.get("wall"):
        hay = (r.url or "") + r.text[:8000]
        if any(w in hay for w in site["wall"]):
            return "error", None
    if r.status_code in site.get("not_found", [404]):
        return "absent", None
    if r.status_code < 400:
        return "found", site.get("conf", "medium")
    return "absent", None


def _h_twitch(u, timeout):
    try:
        r = requests.post("https://gql.twitch.tv/gql",
                          json=[{"query": "query($l:String!){user(login:$l){id}}", "variables": {"l": u.lower()}}],
                          headers={"Client-ID": "kimne78kx3ncx6brgo4mv6wki5h1ko", "Content-Type": "application/json"},
                          timeout=timeout)
        user = (r.json()[0].get("data") or {}).get("user")
        return ("found", "high") if user else ("absent", None)
    except Exception:
        return ("error", None)


def _h_twitter(u, timeout):
    last = "absent"
    seen = set()
    for handle in (u, u.lower()):
        if handle in seen:
            continue
        seen.add(handle)
        try:
            r = requests.get(f"https://api.fxtwitter.com/{handle}",
                             headers={"User-Agent": UA}, timeout=timeout)
            if r.status_code == 200 and (r.json() or {}).get("user"):
                return ("found", "high")
            last = "absent" if r.status_code in (200, 404) else "error"
        except Exception:
            last = "error"
    return (last, None)


def _h_tiktok(u, timeout):
    try:
        r = requests.get("https://www.tiktok.com/oembed",
                         params={"url": f"https://www.tiktok.com/@{u.lower()}"},
                         headers={"User-Agent": UA, "Accept": "application/json"}, timeout=timeout)
        if r.status_code != 200:
            return ("absent", None)
        try:
            data = r.json()
        except ValueError:
            return ("error", None)
        return ("found", "high") if data.get("author_url") else ("absent", None)
    except Exception:
        return ("error", None)


_HANDLERS = {"twitch": _h_twitch, "twitter": _h_twitter, "tiktok": _h_tiktok}


def check(site, username, timeout):
    link = site["link_url"].replace("{u}", username)
    out = {"name": site.get("name"), "cat": site.get("cat") or "other",
           "url": link, "status": "error", "confidence": None,
           "source": site.get("source")}

    if site.get("method") == "custom":
        out["status"], out["confidence"] = _HANDLERS[site["handler"]](username, timeout)
        return out

    headers = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
    if site.get("headers"):
        headers.update(site["headers"])
    try:
        r = requests.get(site["check_url"].replace("{u}", username),
                         headers=headers, cookies=_CONSENT,
                         timeout=timeout, allow_redirects=True)
    except requests.RequestException:
        return out
    if site.get("method") == "status":
        status, conf = _status_eval(site, r)
    else:
        status, conf = _evaluate(site, r.status_code, r.text)
    out["status"] = status
    out["confidence"] = conf
    return out


def iter_results(username, mode, timeout=6, workers=None):
    sites = sites_for(mode)
    if workers is None:
        workers = 20 if mode == "simple" else 60
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(check, s, username, timeout) for s in sites]
        for f in concurrent.futures.as_completed(futs):
            yield f.result()
