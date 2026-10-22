import ipaddress
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def valid_target(s):
    s = (s or "").strip()
    if not s:
        return False
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return "." in s and " " not in s


def search(target, timeout=15):
    target = (target or "").strip()
    if not valid_target(target):
        return {"ok": False, "error": "Enter an IP address or a hostname."}

    try:
        r = requests.get(f"https://ipwho.is/{target}", headers={"User-Agent": UA}, timeout=timeout)
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": "Couldn't reach the geolocation service. Check your connection."}
    except requests.RequestException as e:
        return {"ok": False, "error": f"Request failed: {e}"}

    try:
        d = r.json()
    except ValueError:
        return {"ok": False, "error": "Service returned no parseable data."}

    if not d.get("success"):
        return {"ok": False, "error": d.get("message") or "No data for that target."}

    conn = d.get("connection") or {}
    flag = (d.get("flag") or {})
    lat, lng = d.get("latitude"), d.get("longitude")
    return {
        "ok": True,
        "ip": d.get("ip"),
        "type": d.get("type"),
        "country": d.get("country"),
        "country_code": d.get("country_code"),
        "region": d.get("region"),
        "city": d.get("city"),
        "postal": d.get("postal"),
        "latitude": lat,
        "longitude": lng,
        "timezone": (d.get("timezone") or {}).get("id"),
        "isp": conn.get("isp"),
        "org": conn.get("org"),
        "asn": conn.get("asn"),
        "domain": conn.get("domain"),
        "flag_emoji": flag.get("emoji"),
        "maps_url": (f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
                     if lat is not None and lng is not None else None),
    }
