import requests
from .auth import build_auth_headers, PHOTOS_ORIGIN

PHOTOS_API_KEY = "AIzaSyAa2odBewW-sPJu3jMORr0aNedh3YlkiQc"
BASE = "https://people-pa.clients6.google.com/v2/people"

_FIELDS = [
    "person.metadata.best_display_name",
    "person.photo",
    "person.cover_photo",
    "person.email",
    "person.name",
    "person.metadata",
    "person.in_app_reachability",
    "person.read_only_profile_info",
]
_CONTAINERS = ["PROFILE", "DOMAIN_PROFILE", "ACCOUNT", "CONTACT"]


def _headers(cookies):
    return {
        **build_auth_headers(cookies, PHOTOS_ORIGIN),
        "X-Goog-Api-Key": PHOTOS_API_KEY,
        "Accept": "application/json",
    }


def classify(query: str) -> str:
    q = query.strip()
    if q.isdigit() and len(q) >= 15:
        return "gaia"
    if "@" in q:
        return "email"
    if q.isdigit():
        return "gaia"
    return "invalid"


def lookup(query: str, cookies: dict, timeout: int = 20) -> dict:
    query = query.strip()
    kind = classify(query)
    if kind == "invalid":
        return {"found": False, "error": "Enter an email address or a numeric Gaia ID."}

    if kind == "email":
        url = BASE + "/lookup"
        params = [
            ("id", query), ("type", "EMAIL"), ("match_type", "EXACT"),
            ("core_id_params.enable_private_names", "true"),
        ]
    else:
        url = BASE
        params = [("person_id", query), ("core_id_params.enable_private_names", "true")]

    for f in _FIELDS:
        params.append(("request_mask.include_field.paths", f))
    for c in _CONTAINERS:
        params.append(("request_mask.include_container", c))

    r = None
    for _ in range(2):
        try:
            r = requests.get(url, params=params, headers=_headers(cookies), cookies=cookies, timeout=timeout)
            break
        except requests.exceptions.ConnectionError:
            continue
        except requests.RequestException as e:
            return {"found": False, "error": f"Request failed: {e}"}
    if r is None:
        return {"found": False, "error": "Couldn't reach Google. Check your internet connection, DNS, or VPN, then try again."}

    if r.status_code == 403:
        return {"found": False, "error": "403. Session rejected (cookies expired, or key needs refreshing)."}
    if r.status_code != 200:
        return {"found": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}

    try:
        data = r.json()
    except ValueError:
        return {"found": False, "error": "Response was not JSON."}

    person = _person_from(data, kind)
    if not person:
        return {"found": False, "error": "No match. No discoverable Google account for that input."}

    gaia = _gaia(person) or (query if kind == "gaia" else None)
    if not gaia:
        return {"found": False, "error": "Account found but no Gaia ID exposed."}

    return {
        "found": True,
        "query_type": kind,
        "gaia_id": gaia,
        "name": _name(person),
        "profile_photo": _photo(person, "photo"),
        "cover_photo": _photo(person, "coverPhoto"),
        "emails": _emails(person),
        "last_edit": _last_edit(person),
        "reachable_apps": _reachable(person),
        "services": _services(gaia),
        "raw": person,
    }


def _person_from(data, kind):
    if kind == "email":
        people = (data or {}).get("people") or {}
        if not people:
            return None
        return next(iter(people.values()))
    pr = (data or {}).get("personResponse") or []
    if pr and pr[0].get("status") != "NOT_FOUND":
        return pr[0].get("person")
    return None


def _first(person, key):
    v = person.get(key)
    return v[0] if isinstance(v, list) and v else (v if isinstance(v, dict) else None)


def _gaia(person):
    if str(person.get("personId", "")).isdigit():
        return str(person["personId"])
    meta = person.get("metadata", {}) or {}
    for src in meta.get("identityInfo", {}).get("sourceIds", []):
        sid = str(src.get("id", ""))
        if sid.isdigit():
            return sid
    return None


def _name(person):
    meta = person.get("metadata", {}) or {}
    if meta.get("bestDisplayName", {}).get("displayName"):
        return meta["bestDisplayName"]["displayName"]
    n = _first(person, "name") or {}
    return n.get("displayName") or None


def _photo(person, key):
    p = _first(person, key) or {}
    url = p.get("url") or p.get("imageUrl")
    if url and not p.get("isDefault"):
        return url
    return None


def _emails(person):
    out = []
    for e in person.get("email", []) or []:
        v = e.get("value")
        if v and v not in out:
            out.append(v)
    return out


def _last_edit(person):
    meta = person.get("metadata", {}) or {}
    for k in ("lastUpdateTime", "profileLastUpdateTime"):
        if meta.get(k):
            return meta[k]
    return None


def _reachable(person):
    apps = []
    for r in person.get("inAppReachability", []) or []:
        a = r.get("appType") or r.get("app")
        if a and a not in apps:
            apps.append(a)
    return apps


def _services(gaia):
    return [
        {"name": "Google Maps", "note": "reviews and contributions",
         "url": f"https://www.google.com/maps/contrib/{gaia}/reviews"},
        {"name": "Google Photos", "note": "public album archive",
         "url": f"https://get.google.com/albumarchive/{gaia}"},
        {"name": "Google Account profile", "note": "about page",
         "url": f"https://people.google.com/{gaia}"},
    ]
