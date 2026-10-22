import requests
from .auth import google_headers
from .keys import KEYS

PEOPLE_LOOKUP = "https://people-pa.clients6.google.com/v2/people"


def collect(gaia: str, email, cookies: dict) -> dict:
    return {
        "account": account_info(gaia, cookies),
        "results": [
            calendar_check(email, cookies),
            photos_check(gaia, cookies),
            maps_info(gaia),
        ],
    }


def account_info(gaia: str, cookies: dict) -> dict:
    key, origin = KEYS["photos"]
    headers = google_headers(cookies, origin, key)
    params = [
        ("person_id", gaia),
        ("extension_set.extension_names", "DYNAMITE_ADDITIONAL_DATA"),
        ("extension_set.extension_names", "DYNAMITE_ORGANIZATION_INFO"),
        ("request_mask.include_field.paths", "person.metadata"),
        ("request_mask.include_field.paths", "person.read_only_profile_info"),
        ("request_mask.include_container", "PROFILE"),
        ("request_mask.include_container", "DOMAIN_PROFILE"),
    ]
    try:
        r = requests.get(PEOPLE_LOOKUP, params=params, headers=headers, cookies=cookies, timeout=20)
        person = _first_person(r.json())
    except Exception:
        return {"type": None, "customer_id": None, "entity": None}

    customer_id = _find(person, "customerId")
    entity = _find(person, "entityType")
    return {
        "type": "Workspace / organisation" if customer_id else "Consumer",
        "customer_id": customer_id,
        "entity": entity,
    }


def _first_person(data):
    pr = (data or {}).get("personResponse") or []
    if pr and pr[0].get("status") != "NOT_FOUND":
        return pr[0].get("person") or {}
    people = (data or {}).get("people") or {}
    return next(iter(people.values()), {}) if people else {}


def _find(obj, target):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == target and isinstance(v, (str, int)):
                return v
            got = _find(v, target)
            if got is not None:
                return got
    elif isinstance(obj, list):
        for it in obj:
            got = _find(it, target)
            if got is not None:
                return got
    return None


def calendar_check(email, cookies: dict) -> dict:
    base = {"name": "Google Calendar", "url": None}
    if not email:
        return {**base, "status": "unknown",
                "detail": "Searched by Gaia ID. Give an email to check the calendar."}

    embed = f"https://calendar.google.com/calendar/embed?src={email}"
    base = {"name": "Google Calendar", "url": embed}
    key, origin = KEYS["calendar"]
    headers = google_headers(cookies, origin, key)
    url = f"https://www.googleapis.com/calendar/v3/calendars/{email}/events"
    params = {"key": key, "maxResults": "8", "singleEvents": "true", "orderBy": "startTime"}
    try:
        r = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=15)
    except requests.RequestException:
        return {**base, "status": "unknown", "detail": "Couldn't reach the Calendar API."}

    if r.status_code == 200:
        items = (r.json() or {}).get("items", []) or []
        events = []
        for it in items[:8]:
            start = it.get("start", {})
            events.append({
                "summary": it.get("summary", "(no title)"),
                "when": start.get("dateTime") or start.get("date"),
            })
        return {**base, "status": "active",
                "detail": f"Public calendar with {len(events)} upcoming event(s).",
                "events": events}
    if r.status_code in (403, 404):
        return {**base, "status": "inactive", "detail": "No public calendar."}
    return {**base, "status": "unknown", "detail": f"Calendar API returned HTTP {r.status_code}."}


def photos_check(gaia: str, cookies: dict) -> dict:
    url = f"https://get.google.com/albumarchive/{gaia}"
    base = {"name": "Google Photos (Album Archive)", "url": url}
    try:
        r = requests.get(url, cookies=cookies, allow_redirects=True, timeout=15)
    except requests.RequestException:
        return {**base, "status": "unknown", "detail": "Couldn't reach the album archive."}
    if r.status_code == 200 and "albumarchive" in r.url:
        return {**base, "status": "active", "detail": "Album archive is reachable. Open to view public albums."}
    return {**base, "status": "inactive", "detail": "No reachable public album archive."}


def maps_info(gaia: str) -> dict:
    return {
        "name": "Google Maps",
        "status": "unknown",
        "detail": "Open to view public reviews, ratings and photos.",
        "url": f"https://www.google.com/maps/contrib/{gaia}/reviews",
    }
