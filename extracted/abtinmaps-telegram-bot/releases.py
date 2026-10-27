"""Latest-release lookup for Abtin Maps (GitHub Releases API, cached)."""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass

import httpx

REPO = os.environ.get("GITHUB_REPO", "abtin123/Project")
CACHE_SECONDS = int(os.environ.get("RELEASE_CACHE_SECONDS", "600"))


@dataclass(frozen=True)
class Release:
    version: str       # e.g. "0.0.17"
    apk_url: str       # direct APK link (or the release page if no APK asset)
    page_url: str      # release page


def fallback_release(repo: str = REPO) -> Release:
    page = f"https://github.com/{repo}/releases/latest"
    return Release(version="", apk_url=page, page_url=page)


def pick_release(data: dict, repo: str = REPO) -> Release:
    """Build a Release from a GitHub `releases/latest` API payload."""
    tag = str(data.get("tag_name") or "").strip()
    version = tag.lstrip("vV")
    page = data.get("html_url") or f"https://github.com/{repo}/releases/latest"
    apks = [
        a for a in data.get("assets", [])
        if str(a.get("name", "")).lower().endswith(".apk") and a.get("browser_download_url")
    ]
    # Prefer the app's own APK if a release carries several files.
    apks.sort(key=lambda a: "abtin_maps" not in str(a["name"]).lower())
    apk = apks[0]["browser_download_url"] if apks else page
    return Release(version=version, apk_url=apk, page_url=page)


_cache: Release | None = None
_cache_at = 0.0
_lock = asyncio.Lock()


async def get_release() -> Release:
    """Latest release, cached. Never raises: falls back to the last good value."""
    global _cache, _cache_at
    now = time.monotonic()
    if _cache is not None and now - _cache_at < CACHE_SECONDS:
        return _cache
    async with _lock:
        if _cache is not None and time.monotonic() - _cache_at < CACHE_SECONDS:
            return _cache
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "abtinmaps-telegram-bot"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            async with httpx.AsyncClient(timeout=10, headers=headers) as client:
                r = await client.get(f"https://api.github.com/repos/{REPO}/releases/latest")
                r.raise_for_status()
                _cache = pick_release(r.json())
                _cache_at = time.monotonic()
        except Exception as error:  # network/rate limit/404: keep serving something
            print(f"Release lookup failed: {error}", flush=True)
            if _cache is None:
                return fallback_release()
            _cache_at = time.monotonic() - CACHE_SECONDS + 60  # retry in a minute
        return _cache
