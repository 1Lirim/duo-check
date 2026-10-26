#!/usr/bin/env python3
"""
iPhone Duo Abhol-Checker – Cloud-Version (läuft einmal pro Aufruf, z.B. via GitHub Actions)
Sendet bei Verfügbarkeit einen Push über ntfy.sh (Thema aus Umgebungsvariable NTFY_TOPIC).
"""

import os
import re

import requests

# ------------------------------------------------------------------ Einstellungen
VARIANT_URLS = {
    "512 GB Sternenweiss": "https://www.apple.com/ch-de/shop/buy-iphone/iphone-duo/7,6%E2%80%9D-display-512gb-sternenwei%C3%9F",
    "512 GB Nachthimmel":  "https://www.apple.com/ch-de/shop/buy-iphone/iphone-duo/7,6%E2%80%9D-display-512gb-nachthimmel",
    "1 TB Sternenweiss":   "https://www.apple.com/ch-de/shop/buy-iphone/iphone-duo/7,6%E2%80%9D-display-1tb-sternenwei%C3%9F",
    "256 GB Sternenweiss": "https://www.apple.com/ch-de/shop/buy-iphone/iphone-duo/7,6%E2%80%9D-display-256gb-sternenwei%C3%9F",
}
PART_NUMBERS = {}      # optional manuell: {"512 GB Sternenweiss": "XXXX3SM/A"}
POSTCODE = "8001"
MAX_STORES = 5
# ------------------------------------------------------------------

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
SHOP_URL = "https://www.apple.com/ch-de/shop/buy-iphone/iphone-duo"

s = requests.Session()
s.headers.update({
    "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"),
    "Accept-Language": "de-CH,de;q=0.9",
})


def push(title, msg, priority="urgent"):
    print(f"{title}: {msg}")
    if NTFY_TOPIC:
        s.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode("utf-8"),
               headers={"Title": title, "Priority": priority, "Click": SHOP_URL},
               timeout=10)


def part_number(url):
    html = s.get(url, timeout=20).text
    m = re.findall(r'"partNumber"\s*:\s*"([A-Z0-9]{4,6}\d?[A-Z]{2}/A)"', html) \
        or re.findall(r'\b([A-Z0-9]{5}SM/A)\b', html)
    return m[0] if m else None


def main():
    parts = dict(PART_NUMBERS)
    for name, url in VARIANT_URLS.items():
        if name not in parts:
            pn = part_number(url)
            if pn:
                parts[name] = pn
            else:
                print(f"Keine Teilenummer für {name}")
    if not parts:
        push("iPhone Duo Checker", "Keine Teilenummern gefunden – bitte PART_NUMBERS ausfüllen.", "default")
        return

    params = {"pl": "true", "mts.0": "regular", "location": POSTCODE}
    for i, pn in enumerate(parts.values()):
        params[f"parts.{i}"] = pn
    r = s.get("https://www.apple.com/ch-de/shop/fulfillment-messages", params=params, timeout=20)
    r.raise_for_status()
    stores = (r.json().get("body", {}).get("content", {})
              .get("pickupMessage", {}).get("stores", []))[:MAX_STORES]

    names = {pn: n for n, pn in parts.items()}
    hits = []
    for st in stores:
        for pn, info in (st.get("partsAvailability") or {}).items():
            if info.get("pickupDisplay") == "available":
                hits.append(f"{names.get(pn, pn)} – {st.get('storeName', '?')} "
                            f"{info.get('pickupSearchQuote', '')}".strip())

    if hits:
        push("iPhone Duo verfügbar!", "\n".join(hits))
    else:
        print(f"Nichts verfügbar ({len(parts)} Varianten, {len(stores)} Stores geprüft).")


if __name__ == "__main__":
    main()
