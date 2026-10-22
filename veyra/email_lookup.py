import re
import hashlib
import concurrent.futures
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def valid_email(e):
    return bool(_EMAIL.match((e or "").strip()))


def _r(name, status, confidence=None, url=None):
    return {"name": name, "cat": "email", "status": status,
            "confidence": confidence, "url": url, "source": "email"}


def _m_gravatar(e, timeout):
    h = hashlib.md5(e.lower().encode()).hexdigest()
    try:
        r = requests.get(f"https://gravatar.com/{h}.json", headers={"User-Agent": UA}, timeout=timeout)
    except requests.RequestException:
        return _r("Gravatar", "error")
    if r.status_code == 200:
        url = f"https://gravatar.com/{h}"
        try:
            url = r.json()["entry"][0].get("profileUrl") or url
        except (ValueError, IndexError, KeyError):
            pass
        return _r("Gravatar", "found", "high", url)
    return _r("Gravatar", "absent")


def _m_spotify(e, timeout):
    try:
        r = requests.get("https://spclient.wg.spotify.com/signup/public/v1/account",
                         params={"validate": 1, "email": e}, headers={"User-Agent": UA}, timeout=timeout)
        status = (r.json() or {}).get("status")
    except Exception:
        return _r("Spotify", "error")
    if status == 20:
        return _r("Spotify", "found", "high", "https://open.spotify.com")
    if status == 1:
        return _r("Spotify", "absent")
    return _r("Spotify", "error")


def _m_lastpass(e, timeout):
    try:
        r = requests.get("https://lastpass.com/create_account.php",
                         params={"check": "avail", "skip_login": 1, "username": e},
                         headers={"User-Agent": UA}, timeout=timeout)
        t = r.text.strip().lower()
    except requests.RequestException:
        return _r("LastPass", "error")
    if t == "no":
        return _r("LastPass", "found", "medium", "https://lastpass.com")
    if t == "ok":
        return _r("LastPass", "absent")
    return _r("LastPass", "error")


_MODULES = [("Gravatar", _m_gravatar), ("Spotify", _m_spotify), ("LastPass", _m_lastpass)]


def email_modules():
    return [name for name, _ in _MODULES]


def email_iter(email, timeout=12, workers=8):
    email = email.strip()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(fn, email, timeout) for _, fn in _MODULES]
        for f in concurrent.futures.as_completed(futs):
            yield f.result()
