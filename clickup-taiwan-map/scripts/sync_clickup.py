"""Sync a public anonymized map and an encrypted, full-detail customer map.

Security model: private names, addresses and precise coordinates are *only*
written to AES-GCM ciphertext; never to public JSON, Actions logs, or cache.
"""
import base64
import datetime as dt
import json
import os
import pathlib
import re
import secrets
import unicodedata
from collections import Counter

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIST_ID = "901800292253"
TEXT_ADDRESS_FIELD = "005e585c-bce2-4f59-9dcd-ff1cfbe1aa63"
LOCATION_FIELD = "0e79099e-1e0e-4a5f-a6ef-acdc4da3f1eb"
ITERATIONS = 310_000
CITIES = {
    "基隆市": (25.13, 121.74), "臺北市": (25.03, 121.56),
    "新北市": (25.01, 121.46), "桃園市": (24.99, 121.30),
    "新竹市": (24.81, 120.97), "新竹縣": (24.84, 121.02),
    "苗栗縣": (24.56, 120.82), "臺中市": (24.15, 120.67),
    "彰化縣": (24.08, 120.54), "南投縣": (23.96, 120.97),
    "雲林縣": (23.71, 120.43), "嘉義市": (23.48, 120.45),
    "嘉義縣": (23.45, 120.26), "臺南市": (23.00, 120.23),
    "高雄市": (22.63, 120.30), "屏東縣": (22.55, 120.55),
    "宜蘭縣": (24.76, 121.75), "花蓮縣": (23.99, 121.60),
    "臺東縣": (22.76, 121.14), "澎湖縣": (23.57, 119.58),
    "金門縣": (24.43, 118.32), "連江縣": (26.16, 119.95),
}


def now():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="minutes")


def get_field(task, field_id, name):
    fields = task.get("custom_fields") or []
    for field in fields:
        if field.get("id") == field_id:
            return field.get("value")
    for field in fields:
        if field.get("name") == name:
            return field.get("value")
    return None


def address_string(raw):
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, dict):
        for key in ("formatted_address", "address", "name"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def to_coords(raw):
    if not isinstance(raw, dict):
        return None
    item = raw.get("location", raw)
    if not isinstance(item, dict):
        return None
    try:
        lat = float(item.get("lat", item.get("latitude")))
        lng = float(item.get("lng", item.get("lon", item.get("longitude"))))
        return (lat, lng) if 21 <= lat <= 27 and 117 <= lng <= 124 else None
    except (KeyError, TypeError, ValueError):
        return None


def normalize_address(value):
    value = unicodedata.normalize("NFKC", value).strip()
    value = re.sub(r"^\s*\d{3,6}\s*", "", value)
    value = value.replace("台", "臺")
    # Addresses occasionally contain a full English copy after the Chinese.
    value = re.split(r"\s+(?=(?:NO\.?|No\.?|Taiwan|TAIWAN)\b)", value)[0]
    return re.sub(r"\s+", " ", value)


def city_from_address(address):
    normalized = normalize_address(address)
    for city in CITIES:
        if city in normalized:
            return city
    return ""


def derive_key(password, salt, iterations=ITERATIONS):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    return kdf.derive(password.encode("utf-8"))


def encrypt_json(payload, password):
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    plain = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ct = AESGCM(derive_key(password, salt)).encrypt(iv, plain, None)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    return {"version": 1, "kdf": "PBKDF2-SHA256", "iterations": ITERATIONS,
            "salt": b64(salt), "iv": b64(iv), "ciphertext": b64(ct)}


def read_previous_cache(password):
    path = ROOT / "customers.secure.json"
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text("utf-8"))
        key = derive_key(password, base64.b64decode(doc["salt"]), int(doc["iterations"]))
        plain = AESGCM(key).decrypt(base64.b64decode(doc["iv"]),
                                    base64.b64decode(doc["ciphertext"]), None)
        saved = json.loads(plain)
        return saved.get("geocode_cache") or {}
    except (ValueError, KeyError, TypeError, UnicodeError, json.JSONDecodeError):
        print("Encrypted cache could not be opened; rebuilding without cache.")
        return {}


def geocode(address, api_key, session):
    """Geoapify (Leaflet-compatible). Never publish the input or API key."""
    res = session.get("https://api.geoapify.com/v1/geocode/search",
                      params={"text": address + ", Taiwan", "format": "json",
                              "filter": "countrycode:tw", "lang": "zh",
                              "limit": 1, "apiKey": api_key}, timeout=25)
    res.raise_for_status()
    rows = res.json().get("results") or []
    if not rows:
        return None
    item = rows[0]
    rank = item.get("rank") or {}
    match = rank.get("match_type") or ""
    confidence = float(rank.get("confidence") or 0)
    found_type = item.get("result_type") or ""
    coords = (float(item["lat"]), float(item["lon"]))
    if not (21 <= coords[0] <= 27 and 117 <= coords[1] <= 124):
        return None
    # Do not present city/district centroids as precise house coordinates.
    if confidence >= .65 and (match in ("full_match", "match_by_building", "inner_part")
                               or found_type in ("building", "amenity")):
        quality = "address"
    elif confidence >= .60 and (found_type == "street" or match == "match_by_street"):
        quality = "street"
    else:
        return None
    return {"lat": round(coords[0], 6), "lng": round(coords[1], 6),
            "accuracy": quality, "source": "geoapify"}


def clickup_tasks(token, session):
    all_tasks = []
    for page in range(1000):
        res = session.get(f"https://api.clickup.com/api/v2/list/{LIST_ID}/task",
                          headers={"Authorization": token},
                          params={"page": page, "include_closed": "true",
                                  "subtasks": "false"}, timeout=40)
        res.raise_for_status()
        batch = res.json().get("tasks") or []
        all_tasks.extend(batch)
        if len(batch) < 100:
            return all_tasks
    raise RuntimeError("ClickUp pagination limit exceeded")


def main():
    token = os.environ.get("CLICKUP_TOKEN", "").strip()
    password = os.environ.get("MAP_PASSPHRASE", "")
    api_key = os.environ.get("GEOAPIFY_API_KEY", "").strip()
    if not token:
        raise RuntimeError("Missing CLICKUP_TOKEN repository secret")
    if password and len(password) < 16:
        raise RuntimeError("MAP_PASSPHRASE must be 16+ characters")
    session = requests.Session()
    session.headers["User-Agent"] = "Taiwan-Customer-Atlas/2.0 (ClickUp integration)"
    tasks = clickup_tasks(token, session)
    enabled = bool(password)
    cache = read_previous_cache(password) if enabled else {}
    customers = []
    safe_customers = []
    counts = Counter()
    for task in tasks:
        location = get_field(task, LOCATION_FIELD, "公司地址")
        address = address_string(get_field(task, TEXT_ADDRESS_FIELD, "地址")) or address_string(location)
        coords = to_coords(location)
        city = city_from_address(address)
        if not address and not coords:
            counts["without_address"] += 1
            continue
        quality = "location" if coords else ""
        source = "clickup" if coords else ""
        normalized = normalize_address(address) if address else ""
        if not coords and normalized and api_key and enabled:
            if normalized not in cache:
                try:
                    cache[normalized] = geocode(normalized, api_key, session)
                except (requests.exceptions.RequestException, ValueError, KeyError) as exc:
                    # Abort on a service failure so we do not mistake errors for missing addresses.
                    raise RuntimeError("Geoapify request failed; check API key/quota") from exc
            hit = cache[normalized]
            if hit:
                coords = (hit["lat"], hit["lng"])
                quality = hit["accuracy"]
                source = hit.get("source", "geoapify")
        elif not coords and normalized and enabled and normalized in cache and cache[normalized]:
            hit = cache[normalized]
            coords = (hit["lat"], hit["lng"])
            quality = hit["accuracy"]
            source = hit.get("source", "geoapify")
        if coords and quality in ("location", "address", "street"):
            counts["precise_or_street"] += 1
        if not coords and city:
            coords, quality, source = CITIES[city], "city", "fallback"
        if not coords:
            counts["missing_location"] += 1
            continue
        if quality == "city":
            counts["approximate"] += 1
        # Only publish greatly rounded, anonymized markers.
        safe_customers.append({
            "id": f"c{len(safe_customers)+1}",
            "name": f"客戶 {len(safe_customers)+1:03d}",
            "address": city or "臺灣", "county": city or "其他", "status": "", "url": "",
            "lat": round(coords[0], 1), "lng": round(coords[1], 1),
            "accuracy": "approximate"
        })
        if enabled:
            customers.append({
                "id": task.get("id"), "name": task.get("name") or "(未命名客戶)",
                "address": address, "county": city or "其他",
                "status": (task.get("status") or {}).get("status", ""),
                "url": task.get("url") or "",
                "lat": round(coords[0], 6), "lng": round(coords[1], 6),
                "accuracy": quality, "source": source
            })
    public = {
        "generated_at": now(), "mode": "locked" if enabled else "safe",
        "total_tasks": len(tasks), "located": len(safe_customers),
        "precise_or_street": counts["precise_or_street"],
        "approximate": counts["approximate"],
        "missing_location": counts["missing_location"],
        "without_address": counts["without_address"],
        "customers": safe_customers
    }
    (ROOT / "customers.json").write_text(json.dumps(public, ensure_ascii=False, indent=2), "utf-8")
    if enabled:
        payload = {"generated_at": public["generated_at"], "mode": "private",
                   "total_tasks": len(tasks), "located": len(customers),
                   "precise_or_street": counts["precise_or_street"],
                   "approximate": counts["approximate"],
                   "missing_location": counts["missing_location"],
                   "without_address": counts["without_address"],
                   "customers": customers, "geocode_cache": cache}
        protected = encrypt_json(payload, password)
        (ROOT / "customers.secure.json").write_text(
            json.dumps(protected, ensure_ascii=False, indent=2), "utf-8")
    print(f"Synced {len(tasks)} tasks, {len(safe_customers)} map pins, "
          f"{counts['precise_or_street']} precise/street pins; "
          f"encrypted detail={'enabled' if enabled else 'not configured'}.")


if __name__ == "__main__":
    main()
