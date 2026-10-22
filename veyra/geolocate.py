import re
import requests
from .keys import KEYS

_MAC = re.compile(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$")
GEO_URL = "https://www.googleapis.com/geolocation/v1/geolocate"


def normalize(bssid: str) -> str:
    return bssid.strip().replace("-", ":").lower()


def parse_bssids(text: str):
    parts = re.split(r"[\s,;]+", (text or "").strip())
    return [normalize(p) for p in parts if p]


def geolocate(bssids, timeout: int = 20) -> dict:
    valid = [b for b in bssids if _MAC.match(b)]
    invalid = [b for b in bssids if not _MAC.match(b)]
    if not valid:
        return {"found": False, "error": "Enter at least one valid BSSID (a MAC address like a4:12:34:56:78:9b)."}

    key, origin = KEYS["geolocation"]
    headers = {"X-Goog-Api-Key": key, "Origin": origin, "Referer": origin + "/",
               "Content-Type": "application/json"}
    body = {"considerIp": False, "wifiAccessPoints": [{"macAddress": b} for b in valid]}

    try:
        r = requests.post(f"{GEO_URL}?key={key}", json=body, headers=headers, timeout=timeout)
    except requests.exceptions.ConnectionError:
        return {"found": False, "error": "Couldn't reach Google's geolocation API. Check your connection or DNS."}
    except requests.RequestException as e:
        return {"found": False, "error": f"Request failed: {e}"}

    if r.status_code == 404:
        return {"found": False, "error": "Google couldn't locate these access points. Try adding 2 or more nearby BSSIDs."}
    if r.status_code != 200:
        return {"found": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}

    data = r.json()
    loc = data.get("location", {})
    lat, lng = loc.get("lat"), loc.get("lng")
    if lat is None or lng is None:
        return {"found": False, "error": "No location in the response."}
    return {
        "found": True,
        "lat": lat,
        "lng": lng,
        "accuracy": data.get("accuracy"),
        "used": valid,
        "ignored": invalid,
        "maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lng}",
    }
