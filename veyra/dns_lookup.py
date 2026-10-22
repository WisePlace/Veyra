import ipaddress
import dns.resolver
import dns.reversename
import dns.exception

_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "CAA"]


def _is_ip(s):
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False


def valid_host(s):
    s = (s or "").strip()
    return bool(s) and " " not in s and ("." in s)


def search(target, timeout=6):
    target = (target or "").strip().rstrip(".")
    if not valid_host(target):
        return {"ok": False, "error": "Enter a domain or IP address."}

    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout

    if _is_ip(target):
        try:
            rev = dns.reversename.from_address(target)
            ptr = [str(r).rstrip(".") for r in resolver.resolve(rev, "PTR")]
        except Exception:
            ptr = []
        return {"ok": True, "target": target, "is_ip": True,
                "records": {"PTR": ptr}}

    records = {}
    for t in _TYPES:
        try:
            ans = resolver.resolve(target, t)
            if t == "MX":
                records[t] = sorted(f"{r.preference} {str(r.exchange).rstrip('.')}" for r in ans)
            elif t == "SOA":
                r = list(ans)[0]
                rname = str(r.rname).rstrip(".")
                email = rname.replace(".", "@", 1) if "." in rname else rname
                records[t] = [
                    f"Primary NS: {str(r.mname).rstrip('.')}",
                    f"Responsible: {email}",
                    f"Serial: {r.serial}",
                    f"Refresh: {r.refresh}",
                    f"Retry: {r.retry}",
                    f"Expire: {r.expire}",
                    f"Minimum TTL: {r.minimum}",
                ]
            else:
                records[t] = [str(r).strip('"') if t == "TXT" else str(r).rstrip(".") for r in ans]
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN,
                dns.resolver.NoNameservers, dns.exception.Timeout):
            records[t] = []
        except Exception:
            records[t] = []

    if not any(records.values()):
        return {"ok": False, "error": "No DNS records found (domain may not exist)."}

    return {"ok": True, "target": target, "is_ip": False, "records": records}
