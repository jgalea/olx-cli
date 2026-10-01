import re
import unicodedata

from curl_cffi import requests

BASE = "https://www.olx.pt/api/v1"
PAGE = 50
SORTS = {
    "new": "created_at:desc",
    "cheap": "filter_float_price:asc",
    "dear": "filter_float_price:desc",
}


class OLXError(Exception):
    pass


def _get(path, params=None):
    # OLX sits behind CloudFront, which 403s plain HTTP clients; a Chrome TLS fingerprint gets through.
    r = requests.get(f"{BASE}{path}", params=params, impersonate="chrome", timeout=20)
    if r.status_code != 200:
        raise OLXError(f"{path}: HTTP {r.status_code} {r.text[:200]}")
    return r.json()


def find_city(name):
    data = _get("/geo-encoder/location-autocomplete/", {"query": name})["data"]
    if not data:
        raise OLXError(f"no OLX location matches {name!r}")
    return data[0]["city"]


def _fold(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def _param(offer, key):
    return next((p["value"] for p in offer["params"] if p["key"] == key), {})


def flatten(o):
    price = _param(o, "price")
    return {
        "id": o["id"],
        "title": o["title"],
        "price": price.get("value"),
        "previous_price": price.get("previous_value"),
        "negotiable": price.get("negotiable", False),
        "condition": _param(o, "state").get("label"),
        "city": o["location"].get("city", {}).get("name"),
        "region": o["location"].get("region", {}).get("name"),
        "created": o["created_time"][:10],
        "refreshed": o["last_refresh_time"][:10],
        "business": o["business"],
        "courier": o["contact"].get("courier", False),
        "seller": o["user"].get("name"),
        "url": o["url"],
        "description": o.get("description"),
    }


def search(query, *, min_price=None, max_price=None, condition=None, near=None,
           radius=None, sort=None, limit=50, strict=True):
    params = {"query": query}
    if min_price is not None:
        params["filter_float_price:from"] = min_price
    if max_price is not None:
        params["filter_float_price:to"] = max_price
    if condition:
        params["filter_enum_state[0]"] = condition
    if sort:
        params["sort_by"] = SORTS[sort]
    city = None
    if near:
        city = find_city(near)
        params["city_id"] = city["id"]
        if radius:
            params["distance"] = radius

    # OLX matches loosely (a "philips hue" search returns Philips TVs, and Zigbee bulbs
    # "compatible with Hue"), so by default keep only titles containing every query word.
    words = [_fold(w) for w in re.findall(r"\w+", query)]
    out, total, offset = [], 0, 0
    while len(out) < limit:
        d = _get("/offers/", {**params, "offset": offset, "limit": PAGE})
        total = d["metadata"]["total_elements"]
        for o in d["data"]:
            if not strict or all(w in _fold(o["title"]) for w in words):
                out.append(flatten(o))
        offset += PAGE
        if not d["data"] or offset >= total or not d["links"].get("next"):
            break
    return out[:limit], total, city


def offer(ref):
    m = re.search(r"(\d{6,})", str(ref))
    if m and str(ref).isdigit():
        return flatten(_get(f"/offers/{m.group(1)}/")["data"])
    # Listing URLs carry a slug id (…-IDJAMlD.html), not the numeric id, so look it up via the page.
    r = requests.get(ref, impersonate="chrome", timeout=20)
    m = re.search(r'"sku"\s*:\s*"(\d+)"', r.text) or re.search(r'ad_id["\']?\s*[:=]\s*["\']?(\d{6,})', r.text)
    if not m:
        raise OLXError(f"couldn't find a listing id in {ref}")
    return flatten(_get(f"/offers/{m.group(1)}/")["data"])
