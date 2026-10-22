import os
import json
import logging
import secrets
from flask import (Flask, render_template, request, redirect,
                   url_for, flash, jsonify, Response, stream_with_context)

from veyra.auth import parse_cookie_string, check_cookies
from veyra.people import lookup
from veyra.services import collect as collect_services
from veyra.geolocate import parse_bssids, geolocate
from veyra.drive import scan as drive_scan
from veyra.username import valid_username, sites_for, iter_results
from veyra.email_lookup import valid_email, email_modules, email_iter
from veyra.phone_lookup import search as phone_search
from veyra.cert_lookup import search as cert_search
from veyra.ip_lookup import search as ip_search
from veyra.dns_lookup import search as dns_search
from veyra.person_lookup import build as person_build

if os.environ.get("VEYRA_QUIET"):
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

STATE = {"cookies": None}

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def _connected() -> bool:
    return STATE["cookies"] is not None


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/google/connect")
def google_connect():
    if _connected():
        return redirect(url_for("google_tool"))
    return render_template("connect.html")


@app.route("/google/tool")
def google_tool():
    if not _connected():
        return redirect(url_for("google_connect"))
    return render_template("tools.html")


@app.route("/username")
def username_tool():
    return render_template("username.html")


@app.route("/cert")
def cert_tool():
    return render_template("cert.html")


@app.route("/ip")
def ip_tool():
    return render_template("ip.html")


@app.route("/dns")
def dns_tool():
    return render_template("dns.html")


@app.route("/name")
def name_tool():
    return render_template("name.html")


def _sse(event, obj):
    return f"event: {event}\ndata: {json.dumps(obj)}\n\n"


@app.route("/api/username/stream")
def api_username_stream():
    name = request.args.get("u", "").strip()
    mode = "advanced" if request.args.get("mode") == "advanced" else "simple"
    if not valid_username(name):
        return Response(_sse("error", {"error": "Enter a valid username (letters, digits, dot, dash, underscore)."}),
                        mimetype="text/event-stream")

    def gen():
        sites = sites_for(mode)
        yield _sse("meta", {"total": len(sites), "mode": mode, "username": name})
        found = 0
        for res in iter_results(name, mode):
            if res["status"] == "found":
                found += 1
            yield _sse("result", res)
        yield _sse("done", {"found": found})

    return Response(stream_with_context(gen()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/email/stream")
def api_email_stream():
    email = request.args.get("e", "").strip()
    if not valid_email(email):
        return Response(_sse("error", {"error": "Enter a valid email address."}),
                        mimetype="text/event-stream")

    def gen():
        yield _sse("meta", {"total": len(email_modules()), "email": email})
        found = 0
        for res in email_iter(email):
            if res["status"] == "found":
                found += 1
            yield _sse("result", res)
        yield _sse("done", {"found": found})

    return Response(stream_with_context(gen()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/cert", methods=["POST"])
def api_cert():
    domain = (request.get_json(silent=True) or {}).get("domain", "").strip()
    return jsonify(cert_search(domain))


@app.route("/api/ip", methods=["POST"])
def api_ip():
    target = (request.get_json(silent=True) or {}).get("target", "").strip()
    return jsonify(ip_search(target))


@app.route("/api/dns", methods=["POST"])
def api_dns():
    target = (request.get_json(silent=True) or {}).get("target", "").strip()
    return jsonify(dns_search(target))


@app.route("/api/name", methods=["POST"])
def api_name():
    b = request.get_json(silent=True) or {}
    return jsonify(person_build(b.get("first", ""), b.get("last", ""), b.get("keyword", "")))


@app.route("/api/phone", methods=["POST"])
def api_phone():
    body = request.get_json(silent=True) or {}
    return jsonify(phone_search(body.get("number", ""), body.get("region") or None))


@app.route("/api/ingest", methods=["POST", "OPTIONS"])
def api_ingest():
    if request.method == "OPTIONS":
        return ("", 204, _CORS)
    payload = request.get_json(silent=True) or {}
    cookies = payload.get("cookies") if isinstance(payload.get("cookies"), dict) else payload
    if not isinstance(cookies, dict) or "SAPISID" not in cookies:
        return jsonify({"error": "No SAPISID in received cookies."}), 400, _CORS
    STATE["cookies"] = cookies
    return jsonify({"ok": True}), 200, _CORS


@app.route("/api/status")
def api_status():
    return jsonify({"connected": _connected()})


@app.route("/connect", methods=["POST"])
def connect_cookies():
    cookies = parse_cookie_string(request.form.get("cookies", ""))
    if "SAPISID" not in cookies:
        flash("No SAPISID cookie in what you pasted.", "error")
        return redirect(url_for("google_connect"))
    try:
        valid = check_cookies(cookies)
    except Exception as e:
        flash(f"Couldn't reach Google to validate: {e}", "error")
        return redirect(url_for("google_connect"))
    if not valid:
        flash("Cookies look invalid or expired.", "error")
        return redirect(url_for("google_connect"))
    STATE["cookies"] = cookies
    return redirect(url_for("google_tool"))


@app.route("/disconnect")
def disconnect():
    STATE["cookies"] = None
    return redirect(url_for("google_connect"))


@app.route("/api/lookup", methods=["POST"])
def api_lookup():
    if not _connected():
        return jsonify({"error": "Not connected."}), 401
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        return jsonify({"found": False, "error": "Enter an email address or a Gaia ID."}), 400
    result = lookup(query, STATE["cookies"])
    if body.get("services") and result.get("found"):
        email = result.get("emails", [None])[0] if result.get("emails") else (
            query if result.get("query_type") == "email" else None)
        try:
            result["services_data"] = collect_services(result["gaia_id"], email, STATE["cookies"])
        except Exception as e:
            result["services_data"] = {"error": f"Service fetch failed: {e}"}
    return jsonify(result)


@app.route("/api/geolocate", methods=["POST"])
def api_geolocate():
    if not _connected():
        return jsonify({"error": "Not connected."}), 401
    raw = (request.get_json(silent=True) or {}).get("bssids", "")
    bssids = parse_bssids(raw)
    if not bssids:
        return jsonify({"found": False, "error": "Enter one or more BSSIDs (MAC addresses)."}), 400
    return jsonify(geolocate(bssids))


@app.route("/api/drive", methods=["POST"])
def api_drive():
    if not _connected():
        return jsonify({"error": "Not connected."}), 401
    link = (request.get_json(silent=True) or {}).get("link", "").strip()
    if not link:
        return jsonify({"found": False, "error": "Paste a Google Drive or Docs link."}), 400
    return jsonify(drive_scan(link, STATE["cookies"]))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
