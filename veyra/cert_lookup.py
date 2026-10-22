import re
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_DOMAIN = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})+$")


def valid_domain(d):
    return bool(_DOMAIN.match((d or "").strip().lower()))


def search(domain, timeout=40):
    domain = (domain or "").strip().lower().lstrip("*.")
    if not valid_domain(domain):
        return {"ok": False, "error": "Enter a valid domain (e.g. example.com)."}

    try:
        r = requests.get("https://crt.sh/", params={"q": f"%.{domain}", "output": "json"},
                         headers={"User-Agent": UA}, timeout=timeout)
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": "Couldn't reach crt.sh. Check your connection or try again."}
    except requests.RequestException as e:
        return {"ok": False, "error": f"Request failed: {e}"}

    if r.status_code != 200:
        return {"ok": False, "error": f"crt.sh returned HTTP {r.status_code}."}
    try:
        rows = r.json()
    except ValueError:
        return {"ok": False, "error": "crt.sh returned no parseable data (it may be rate-limited)."}

    subs = set()
    certs = []
    for row in rows:
        for name in (row.get("name_value") or "").split("\n"):
            name = name.strip().lower().lstrip("*.")
            if name and (name == domain or name.endswith("." + domain)):
                subs.add(name)
        certs.append({
            "common_name": row.get("common_name"),
            "issuer": row.get("issuer_name"),
            "not_before": row.get("not_before"),
            "not_after": row.get("not_after"),
        })

    certs.sort(key=lambda c: c.get("not_before") or "", reverse=True)
    return {
        "ok": True,
        "domain": domain,
        "count": len(subs),
        "subdomains": sorted(subs),
        "certs": certs[:25],
        "total_certs": len(rows),
    }
