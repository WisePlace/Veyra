# Veyra

A self-built OSINT toolkit. First tool: resolve a Google email address to its
**Gaia ID** (the permanent numeric account identifier). Built from scratch,
informed by how GHunt talks to Google's internal APIs no GHunt code is reused.

```
┌────────────┐ sign in once ┌──────────────┐ signed request ┌───────────────┐
│ connect │ ────────────────► │ Flask backend │ ──────────────────► │ Google │
│ page │ │ (SAPISIDHASH) │ ◄───── Gaia ID ──── │ people-pa API │
└────────────┘ └──────────────┘ └───────────────┘
```

## Why it works the way it does

- **Not OAuth.** The emailtoGaia lookup uses Google's *internal* People API
 (`people-pa.clients6.google.com`), which the official OAuth People API won't
 do. So connecting an account means supplying that account's **consumer
 session cookies**, not a Sign-in-with-Google button.
- **Backend, not pure frontend.** Those endpoints block cross-origin browser
 requests (CORS), and signing needs the cookies server-side. The webpage is a
 frontend to the local Flask backend.
- **SAPISIDHASH.** Each request is signed with
 `<ts>_sha1("<ts> <SAPISID> <origin>")`, the scheme Google's own web apps use.

## Quick start

**Windows:** double-click **`start.bat`**. The first run sets up a virtual
environment and installs the two dependencies, then opens Veyra in your browser;
later runs start instantly. (Needs Python 3 installed, with "Add Python to PATH"
ticked.)

**macOS / Linux:** run `./start.sh`.

Prefer to do it by hand? See *Setup* below.

## Setup

```bash
cd veyra
python -m venv .venv && source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Connecting (your own burner account)

Veyra does **not** automate a Google login Google blocks sign-in inside
automated browsers ("this browser may not be secure"). Instead, the **Veyra
Connect** extension reads the session from the browser you're already logged
into and sends it to the app. The browser's own cookies API returns the
decrypted values (HttpOnly ones included), so Windows app-bound cookie
encryption isn't a problem.

The home page (`/`) lists the tools; **Google Services** opens the connect page,
which offers two choices:

**Connect using the extension** (recommended)
- One-time: open `chrome://extensions` (or `brave://` / `edge://extensions`) to
 **Developer mode** to **Load unpacked** to select `extension/veyra-connect/` to pin it.
- The connect page detects whether the extension is installed and shows a short
 install tutorial if it isn't.
- Each time: be logged into your burner in that browser, click the **Veyra
 Connect** icon to **Send session to Veyra**. The page advances on its own.

**Connect with a session cookie** (fallback)
- Paste a `Cookie:` header. The quickest way to get one is the extension's
 **Copy session cookie** button; otherwise DevTools to Network to a
 `photos.google.com` request to copy the `Cookie:` header.

The session is kept in memory only; **Disconnect** drops it.

### The Veyra Connect extension
Two buttons: **Send session to Veyra** (POSTs the Google cookies to the app) and
**Copy session cookie** (puts the `name=value; …` string on your clipboard for
the paste path). A content script tags Veyra's pages so the app can tell the
extension is installed. It reads Google cookies via the browser's own API, so
HttpOnly cookies are included and Windows cookie encryption isn't a problem.

### Branding
The logo is a single file: `static/veyra-mark.svg`. Replace it with your exported
SVG to update the favicon, header, home hero, and extension icon at once. The
brand palette lives in `:root` at the top of `static/style.css`.

## Project layout

```
veyra/
├── app.py # Flask routes: home / google connect+tool / ingest / status / gaia
├── veyra/
│ ├── auth.py # cookie parsing, SAPISIDHASH, session validation
│ └── people.py # the People API call + Gaia-ID extraction
├── extension/
│ └── veyra-connect/ # browser extension
│ ├── manifest.json
│ ├── content.js # tags Veyra pages so the app can detect the extension
│ ├── popup.html
│ └── popup.js # Send session / Copy session cookie
├── templates/ # base.html, home.html, connect.html, tools.html
├── static/
│ ├── style.css # brand palette in :root
│ └── veyra-mark.svg # the logo (swap this one file to rebrand)
└── requirements.txt
```

## Tools (Google Services)

Once connected, the Google Services tool has three tabs:

- **Identity** look up an account by email or Gaia ID: Gaia ID, name, profile/
 cover photos, emails, last edit, reachable apps. Tick **Fetch service data** to
 also probe Google Calendar (public events), Google Photos (album-archive
 reachability), Google Maps (contributions link), and the account type
 (Consumer vs Workspace/organisation). **Raw JSON** toggles the full response.
- **Wi-Fi** geolocate from one or more **BSSIDs** (access-point MAC addresses,
 not the network name). Google usually needs 2+ nearby BSSIDs for a fix.
- **Drive** paste a public Drive/Docs/Sheets/Slides link to read its metadata:
 name, type, owner, timestamps, sharing, permissions.

### Status of each piece
- Solid: Identity lookup, Wi-Fi geolocate (key-only API), Drive metadata.
- Best-effort (endpoints shift; untested against a live account from the build
 box): Calendar events, Photos reachability, account-type detection.
- Link-only for now: Maps review **contents** (protobuf endpoint left as a
 link; active/inactive detection is the natural next step).
- Not supported: Google Play Games (needs the Android master-token auth flow,
 which the cookie session here doesn't provide).


## Lookup tool (username / email / phone)

Independent of the Google connection. Three types:

- Username: Simple (top platforms) or Advanced (1,160 reliable sites merged from WhatsMyName and Maigret). Results stream live and each hit is scored high/medium/low by how reliably exist-vs-missing could be confirmed.
- Email: Gravatar identity (name, location, linked accounts) plus the MD5 hash.
- Phone: validity, country, carrier, line type and timezones via the phonenumbers library.

## Adding the next tool

Same shape each time: build auth headers (`auth.build_auth_headers`, maybe a
different origin/key), hit the service endpoint, parse. Add a function in a new
`veyra/*.py`, a route in `app.py`, a form on the tools page. Good next steps off
a Gaia ID: profile picture, public Maps reviews, public Calendar.

## Caveats

- **Undocumented endpoints.** Google changes params and keys without notice. If
 lookups start returning 403/empty, re-check the request in your browser's
 Network tab and update the key/params in `veyra/people.py`.
- **Session expiry.** Cookies eventually rotate. When lookups start failing with
 403, just click **Send session to Veyra** again.
- **Rate limits.** A fresh account hammering lookups can get throttled. Go slow.
- **Scope of use.** Automating these endpoints is against Google's ToS (hence a
 burner). It returns only data Google exposes to any signed-in user. Running it
 against identifiable people is regulated (GDPR profiling) keep it to your own
 accounts and authorized engagements.
