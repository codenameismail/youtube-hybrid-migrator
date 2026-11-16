"""Step 2: channel subscriptions."""
import json
import time
from hashlib import sha1

import requests
from ytmusicapi import YTMusic
from ytmusicapi.helpers import sapisid_from_cookie

import config
import util


def _walk_fe_channels(node, found, continuations):
    """Recursively extract channelRenderer IDs and continuation tokens from InnerTube JSON."""
    if isinstance(node, dict):
        cr = node.get("channelRenderer") or node.get("gridChannelRenderer")
        if isinstance(cr, dict) and cr.get("channelId"):
            cid = cr["channelId"]
            title_obj = cr.get("title", {})
            title = (
                title_obj.get("simpleText")
                or "".join(r.get("text", "") for r in title_obj.get("runs", []))
                or "Unknown"
            )
            found[cid] = title
        tok = (
            node.get("continuationItemRenderer", {})
            .get("continuationEndpoint", {})
            .get("continuationCommand", {})
            .get("token")
        )
        if tok:
            continuations.append(tok)
        for v in node.values():
            _walk_fe_channels(v, found, continuations)
    elif isinstance(node, list):
        for item in node:
            _walk_fe_channels(item, found, continuations)


def _read_web_fe_channels(headers_path):
    """Fetch ALL subscribed channels directly from www.youtube.com/feed/channels (FEchannels)."""
    raw = json.loads(headers_path.read_text(encoding="utf-8"))
    cookie = raw.get("cookie") or raw.get("Cookie", "")
    sapisid = sapisid_from_cookie(cookie)
    origin = "https://www.youtube.com"

    def make_headers():
        ts = str(int(time.time()))
        digest = sha1(f"{ts} {sapisid} {origin}".encode("utf-8")).hexdigest()
        h = {
            "User-Agent": raw.get("user-agent", "Mozilla/5.0"),
            "Accept-Language": raw.get("accept-language", "en-US,en;q=0.9"),
            "Content-Type": "application/json",
            "Cookie": cookie,
            "Origin": origin,
            "X-Origin": origin,
            "X-Goog-AuthUser": str(raw.get("x-goog-authuser", "0")),
            "Authorization": f"SAPISIDHASH {ts}_{digest} SAPISID1PHASH {ts}_{digest} SAPISID3PHASH {ts}_{digest}",
        }
        # Preserve Brand Account / sub-channel session identity if present in headers
        for key in ("x-goog-pageid", "X-Goog-PageId"):
            if key in raw:
                h["X-Goog-PageId"] = str(raw[key])
        return h

    context = {
        "client": {
            "clientName": "WEB",
            "clientVersion": "2.20261110.01.00",
            "hl": "en",
        }
    }

    found = {}
    payload = {"context": context, "browseId": "FEchannels"}
    session = requests.Session()

    while payload:
        resp = session.post(
            "https://www.youtube.com/youtubei/v1/browse?prettyPrint=false",
            headers=make_headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        continuations = []
        _walk_fe_channels(data, found, continuations)
        payload = {"context": context, "continuation": continuations[-1]} if continuations else None

    return [{"id": cid, "title": title} for cid, title in found.items()]


def _collect_all_old_subs(old_api):
    """Combine official API subscriptions with InnerTube web + YTMusic subscriptions if old_headers.json exists."""
    merged = {s["id"]: s["title"] for s in old_api.list_subscriptions()}
    api_count = len(merged)

    if config.OLD_HEADERS.exists():
        # 1. Read from www.youtube.com FEchannels (same source as youtube.com/feed/channels)
        try:
            web_subs = _read_web_fe_channels(config.OLD_HEADERS)
            for s in web_subs:
                merged.setdefault(s["id"], s["title"])
            print(f"  + Web FEchannels found {len(web_subs)} channels (API alone saw {api_count}).")
        except Exception as e:
            print(f"  ! Couldn't read FEchannels via {config.OLD_HEADERS.name}: {e}")

        # 2. Read from YouTube Music artist & audio channel subscriptions
        try:
            old_music = YTMusic(str(config.OLD_HEADERS))
            for getter in (old_music.get_library_subscriptions, old_music.get_library_channels):
                try:
                    items = getter(limit=None) or []
                    for item in items:
                        cid = item.get("browseId")
                        if cid and cid.startswith("UC"):
                            merged.setdefault(cid, item.get("artist") or item.get("title") or "Unknown")
                except Exception:
                    pass
        except Exception as e:
            print(f"  ! Couldn't read YTMusic subs via {config.OLD_HEADERS.name}: {e}")
    else:
        print(
            f"  (Note: Official YouTube API returned {api_count} channels. If youtube.com/feed/channels "
            f"shows more, create {config.OLD_HEADERS.relative_to(config.ROOT)} from your OLD account "
            f"to read hidden Music/Kids/Topic subscriptions automatically.)"
        )

    return [{"id": cid, "title": title} for cid, title in merged.items()]


def run(old_api, new_music, get_new_api=None):
    print("\n[SUBS] Reading subscriptions from the OLD account...")
    old_subs = _collect_all_old_subs(old_api)
    if not old_subs:
        print("No subscriptions found.")
        return
    print(f"Found {len(old_subs)} total channels.")

    # YouTube Music only lists music artists, so a local memory file covers the rest.
    already = util.read_set(config.SUBS_MEMORY)
    try:
        subs = new_music.get_library_subscriptions(limit=None) or []
        already |= {s["browseId"] for s in subs if s.get("browseId")}
    except Exception as e:
        print(f"Couldn't read existing subscriptions on the NEW account ({e}). Using local memory only.")

    old_subs.reverse()

    done = skipped = failed = 0
    for i, sub in enumerate(old_subs, 1):
        tag = f"[{i}/{len(old_subs)}]"
        if sub["id"] in already:
            skipped += 1
            continue
        try:
            new_music.subscribe_artists([sub["id"]])
            util.append_line(config.SUBS_MEMORY, sub["id"])
            done += 1
            print(f"{tag} Subscribed: {sub['title']}")
            util.pause()
        except Exception as e:
            # Fallback to official YouTube API if YTMusic rejects a specific channel type
            if get_new_api is not None:
                try:
                    new_api = get_new_api()
                    new_api.service.subscriptions().insert(
                        part="snippet",
                        body={"snippet": {"resourceId": {"kind": "youtube#channel", "channelId": sub["id"]}}},
                    ).execute()
                    util.append_line(config.SUBS_MEMORY, sub["id"])
                    done += 1
                    print(f"{tag} Subscribed (via YouTube API): {sub['title']}")
                    continue
                except Exception as api_err:
                    e = api_err
            failed += 1
            print(f"{tag} Failed: {sub['title']} - {e}")

    print(f"[SUBS] Done. Newly subscribed: {done}, already done: {skipped}, failed: {failed}.")
