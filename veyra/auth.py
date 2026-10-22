import hashlib
import time
import requests

PHOTOS_ORIGIN = "https://photos.google.com"


def parse_cookie_string(raw: str) -> dict:
    jar = {}
    for part in raw.strip().strip(";").split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        jar[name.strip()] = value.strip()
    return jar


def gen_sapisidhash(sapisid: str, origin: str = PHOTOS_ORIGIN) -> str:
    ts = str(int(time.time()))
    digest = hashlib.sha1(f"{ts} {sapisid} {origin}".encode()).hexdigest()
    return f"{ts}_{digest}"


def build_auth_headers(cookies: dict, origin: str = PHOTOS_ORIGIN) -> dict:
    sapisid = cookies.get("SAPISID") or cookies.get("__Secure-3PAPISID")
    if not sapisid:
        raise ValueError("No SAPISID cookie found.")
    return {
        "Authorization": f"SAPISIDHASH {gen_sapisidhash(sapisid, origin)}",
        "Origin": origin,
        "Referer": origin + "/",
    }


def google_headers(cookies: dict, origin: str, api_key: str, sign: bool = True) -> dict:
    h = {"X-Goog-Api-Key": api_key, "Accept": "application/json"}
    if sign:
        h.update(build_auth_headers(cookies, origin))
    else:
        h.update({"Origin": origin, "Referer": origin + "/"})
    return h


def check_cookies(cookies: dict, timeout: int = 15) -> bool:
    r = requests.get(
        "https://accounts.google.com/CheckCookie",
        params={"continue": "https://www.google.com/robots.txt"},
        cookies=cookies,
        allow_redirects=False,
        timeout=timeout,
    )
    location = r.headers.get("Location", "")
    return r.status_code in (301, 302) and not location.startswith(
        ("https://support.google.com", "https://accounts.google.com/CookieMismatch")
    )
