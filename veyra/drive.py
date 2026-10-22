import re
import requests
from .auth import google_headers
from .keys import KEYS

_ID_PATTERNS = [
    r"/d/([a-zA-Z0-9_-]{10,})",
    r"/file/d/([a-zA-Z0-9_-]{10,})",
    r"/folders/([a-zA-Z0-9_-]{10,})",
    r"[?&]id=([a-zA-Z0-9_-]{10,})",
]

_FIELDS = (
    "id,title,mimeType,description,fileSize,createdDate,modifiedDate,"
    "ownerNames,owners(displayName,emailAddress,picture/url),"
    "lastModifyingUserName,shared,alternateLink,fileExtension,md5Checksum,"
    "permissions(id,type,role,emailAddress,name,domain)"
)

DRIVE_URL = "https://clients6.google.com/drive/v2internal/files"


def extract_id(text: str):
    text = (text or "").strip()
    for pat in _ID_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", text):
        return text
    return None


def scan(link: str, cookies: dict, timeout: int = 20) -> dict:
    fid = extract_id(link)
    if not fid:
        return {"found": False, "error": "Couldn't find a Drive file or folder ID in that link."}

    key, origin = KEYS["drive"]
    headers = google_headers(cookies, origin, key)
    params = {"fields": _FIELDS, "supportsAllDrives": "true", "key": key}

    try:
        r = requests.get(f"{DRIVE_URL}/{fid}", params=params, headers=headers, cookies=cookies, timeout=timeout)
    except requests.exceptions.ConnectionError:
        return {"found": False, "error": "Couldn't reach Google Drive. Check your connection or DNS."}
    except requests.RequestException as e:
        return {"found": False, "error": f"Request failed: {e}"}

    if r.status_code in (401, 403, 404):
        return {"found": False, "error": "File not found, or it isn't shared with your account."}
    if r.status_code != 200:
        return {"found": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}

    f = r.json()
    owners = f.get("owners", []) or []
    owner = owners[0] if owners else {}
    is_folder = f.get("mimeType") == "application/vnd.google-apps.folder"
    return {
        "found": True,
        "id": f.get("id"),
        "name": f.get("title"),
        "kind": "Folder" if is_folder else (f.get("mimeType") or "file"),
        "description": f.get("description"),
        "size": f.get("fileSize"),
        "created": f.get("createdDate"),
        "modified": f.get("modifiedDate"),
        "owner_name": owner.get("displayName") or (f.get("ownerNames") or [None])[0],
        "owner_email": owner.get("emailAddress"),
        "owner_photo": (owner.get("picture") or {}).get("url"),
        "last_modifier": f.get("lastModifyingUserName"),
        "shared": f.get("shared"),
        "web_link": f.get("alternateLink"),
        "permissions": f.get("permissions"),
        "raw": f,
    }
