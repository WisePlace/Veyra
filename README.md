# Veyra

Self-built OSINT toolkit.

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

# Tools

## Google Services

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

## Lookup tool (username / email / phone)

Independent of the Google connection. Three types:

- Username: Simple (top platforms) or Advanced (1,160 reliable sites merged from WhatsMyName and Maigret). Results stream live and each hit is scored high/medium/low by how reliably exist-vs-missing could be confirmed.
- Email: Gravatar identity (name, location, linked accounts) plus the MD5 hash.
- Phone: validity, country, carrier, line type and timezones via the phonenumbers library.

## Disclaimer

- **Scope of use.** Automating these endpoints is against Google's ToS (hence a
 burner). It returns only data Google exposes to any signed-in user. Running it
 against identifiable people is regulated (GDPR profiling) keep it to your own
 accounts and authorized engagements.
