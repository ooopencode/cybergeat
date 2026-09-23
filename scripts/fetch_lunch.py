"""定时抓取：用 AMAP_API_KEY（环境变量）拉园区周边美食，写成静态 candidates.json。
供 GitHub Pages 纯前端直接读取，公网不暴露 key。
用法：AMAP_API_KEY=xxx python scripts/fetch_lunch.py [--out candidates.json]
"""
import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone, timedelta

import requests

# 唯一真相：高德地理编码 "深圳新一代产业园" 的 GCJ02 坐标（中康路136号）
CENTER_GCJ02 = (114.061104, 22.573133)
CENTER_NAME = "深圳新一代产业园"
RADIUS = 800

pi = 3.1415926535897932384626
a = 6378245.0
ee = 0.00669342162296594323


def _transformlat(lng, lat):
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + \
          0.1 * lng * lat + 0.2 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 *
            math.sin(2.0 * lng * pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * pi) + 40.0 *
            math.sin(lat / 3.0 * pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * pi) + 320 *
            math.sin(lat * pi / 30.0)) * 2.0 / 3.0
    return ret


def _transformlng(lng, lat):
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + \
          0.1 * lng * lat + 0.1 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 *
            math.sin(2.0 * lng * pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * pi) + 40.0 *
            math.sin(lng / 3.0 * pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * pi) + 300.0 *
            math.sin(lng / 30.0 * pi)) * 2.0 / 3.0
    return ret


def gcj02_to_wgs84(lng, lat):
    if not (73.66 < lng < 135.05 and 3.86 < lat < 53.55):
        return lng, lat
    dlat = _transformlat(lng - 105.0, lat - 35.0)
    dlng = _transformlng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * pi)
    mglat = lat + dlat
    mglng = lng + dlng
    return lng * 2 - mglng, lat * 2 - mglat


def _to_float(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _to_int(s, default=0):
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="candidates.json")
    args = ap.parse_args()

    key = os.getenv("AMAP_API_KEY", "").strip()
    if not key or "你的高德" in key:
        print("ERROR: 请设置 AMAP_API_KEY 环境变量", file=sys.stderr)
        return 1

    gcj_lng, gcj_lat = CENTER_GCJ02
    all_pois = []
    for page in range(1, 4):
        try:
            resp = requests.get(
                "https://restapi.amap.com/v3/place/around",
                params={
                    "key": key,
                    "location": f"{gcj_lng},{gcj_lat}",
                    "keywords": "美食",
                    "types": "050000",
                    "radius": RADIUS,
                    "offset": 25,
                    "page": page,
                    "extensions": "all",
                },
                timeout=10,
            ).json()
            if resp.get("status") != "1":
                print(f"AMap Error p{page}: {resp.get('info')}")
                break
            pois = resp.get("pois", [])
            if not pois:
                break
            all_pois.extend(pois)
        except Exception as e:
            print(f"Request Error p{page}: {e}")
            break

    results = []
    for poi in all_pois:
        name = (poi.get("name") or "").strip()
        if not name:
            continue
        loc = (poi.get("location") or "0,0").split(",")
        try:
            plng, plat = float(loc[0]), float(loc[1])
        except ValueError:
            continue
        wlng, wlat = gcj02_to_wgs84(plng, plat)
        biz = poi.get("biz_ext") or {}
        rating = None if isinstance(biz.get("rating"), list) else _to_float(biz.get("rating"))
        cost = None if isinstance(biz.get("cost"), list) else _to_int(biz.get("cost"), None)
        if isinstance(cost, float):
            cost = None
        results.append({
            "id": poi.get("id"),
            "name": name,
            "lat": wlat,
            "lng": wlng,
            "rating": rating,
            "price": cost,
            "distance": _to_int(poi.get("distance"), 0),
        })

    wlng, wlat = gcj02_to_wgs84(*CENTER_GCJ02)
    bj = timezone(timedelta(hours=8))
    payload = {
        "updated_at": datetime.now(bj).strftime("%Y-%m-%d %H:%M"),
        "center": {"name": CENTER_NAME, "lat": wlat, "lng": wlng},
        "count": len(results),
        "results": results,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Wrote {args.out}: {len(results)} places")
    return 0 if results else 2


if __name__ == "__main__":
    raise SystemExit(main())
