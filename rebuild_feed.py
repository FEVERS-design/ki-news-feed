#!/usr/bin/env python3
"""
rebuild_feed.py – Einmaliges Reparatur-Skript
---------------------------------------------
Baut docs/feed.xml komplett neu aus ALLEN MP3-Dateien in docs/episodes/.
Nutzt das exakt gleiche Format wie publish_podcast.py, damit der laufende
Bot danach nahtlos weiter anhängt.

Aufruf (im Wurzelverzeichnis des ki-news-feed-Repos):
    python rebuild_feed.py

Voraussetzung:
    pip install mutagen
    Die MP3s liegen unter docs/episodes/ki-news-YYYY-MM-DD.mp3

Das Skript überschreibt docs/feed.xml. Die MP3s bleiben unangetastet.
"""

import os
import re
import glob
import datetime as dt
from email.utils import format_datetime
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

from mutagen.mp3 import MP3

# ----------------------------------------------------------------------
# Muss mit publish_podcast.py übereinstimmen
# ----------------------------------------------------------------------
BASE_URL = "https://fevers-design.github.io/ki-news-feed"

DOCS_DIR = "docs"
EPISODES_DIR = os.path.join(DOCS_DIR, "episodes")
FEED_PATH = os.path.join(DOCS_DIR, "feed.xml")

PODCAST_TITLE = "Wöchentliche KI-News"
PODCAST_DESCRIPTION = (
    "Jede Woche die wichtigsten KI-Nachrichten und Forschungsbeiträge, "
    "automatisch zusammengefasst und vertont."
)
PODCAST_AUTHOR = "KI-News-Bot"
PODCAST_EMAIL = "eversf05@gmail.com"
PODCAST_LANGUAGE = "de"
PODCAST_CATEGORY = "Technology"

# Einheitliche Uhrzeit für abgeleitete pubDates (wie bei der echten 17.07.-Folge)
PUB_HOUR_UTC = 17
PUB_MIN_UTC = 15

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ATOM_NS = "http://www.w3.org/2005/Atom"

# Dateiname: ki-news-YYYY-MM-DD.mp3
NAME_RE = re.compile(r"ki-news-(\d{4})-(\d{2})-(\d{2})\.mp3$")


def _fmt_duration(seconds: int) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"


def collect_episodes():
    """Liest alle MP3s, sortiert nach Datum absteigend (neueste zuerst)."""
    episodes = []
    for path in glob.glob(os.path.join(EPISODES_DIR, "ki-news-*.mp3")):
        fname = os.path.basename(path)
        m = NAME_RE.search(fname)
        if not m:
            print(f"  übersprungen (Name passt nicht): {fname}")
            continue
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        pub = dt.datetime(year, month, day, PUB_HOUR_UTC, PUB_MIN_UTC,
                          tzinfo=dt.timezone.utc)
        try:
            duration = int(MP3(path).info.length)
        except Exception as e:
            print(f"  WARN: Dauer nicht lesbar für {fname}: {e} -> 0")
            duration = 0
        size = os.path.getsize(path)
        episodes.append({
            "fname": fname,
            "date": dt.date(year, month, day),
            "pub": pub,
            "duration": duration,
            "size": size,
        })
    episodes.sort(key=lambda e: e["pub"], reverse=True)  # neueste oben
    return episodes


def build_item(ep) -> str:
    title = f"KI-News – {ep['date'].strftime('%d.%m.%Y')}"
    desc = "Die wichtigsten KI-Entwicklungen der Woche, automatisch zusammengefasst."
    mp3_url = f"{BASE_URL}/episodes/{ep['fname']}"
    return f"""    <item>
      <title>{escape(title)}</title>
      <description>{escape(desc)}</description>
      <itunes:summary>{escape(desc)}</itunes:summary>
      <enclosure url="{escape(mp3_url)}" length="{ep['size']}" type="audio/mpeg"/>
      <guid isPermaLink="false">{escape(mp3_url)}</guid>
      <pubDate>{format_datetime(ep['pub'])}</pubDate>
      <itunes:duration>{_fmt_duration(ep['duration'])}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>
"""


def build_feed(episodes) -> str:
    now = format_datetime(dt.datetime.now(dt.timezone.utc))
    cover_url = f"{BASE_URL}/cover.jpg"
    feed_url = f"{BASE_URL}/feed.xml"
    items = "".join(build_item(ep) for ep in episodes)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="{ITUNES_NS}"
     xmlns:atom="{ATOM_NS}">
  <channel>
    <title>{escape(PODCAST_TITLE)}</title>
    <link>{escape(BASE_URL)}</link>
    <atom:link href="{escape(feed_url)}" rel="self" type="application/rss+xml"/>
    <language>{PODCAST_LANGUAGE}</language>
    <description>{escape(PODCAST_DESCRIPTION)}</description>
    <itunes:author>{escape(PODCAST_AUTHOR)}</itunes:author>
    <itunes:summary>{escape(PODCAST_DESCRIPTION)}</itunes:summary>
    <itunes:explicit>false</itunes:explicit>
    <itunes:image href="{escape(cover_url)}"/>
    <itunes:category text="{escape(PODCAST_CATEGORY)}"/>
    <itunes:owner>
      <itunes:name>{escape(PODCAST_AUTHOR)}</itunes:name>
      <itunes:email>{escape(PODCAST_EMAIL)}</itunes:email>
    </itunes:owner>
    <lastBuildDate>{now}</lastBuildDate>
<!-- ITEMS -->
{items}  </channel>
</rss>
"""


def main():
    if not os.path.isdir(EPISODES_DIR):
        raise SystemExit(f"Ordner nicht gefunden: {EPISODES_DIR} "
                         f"(Skript im Repo-Wurzelverzeichnis ausführen)")
    episodes = collect_episodes()
    if not episodes:
        raise SystemExit("Keine MP3s gefunden – nichts zu tun.")

    print(f"{len(episodes)} Folgen gefunden:")
    for ep in episodes:
        print(f"  {ep['date']}  {_fmt_duration(ep['duration']):>7}  {ep['fname']}")

    feed = build_feed(episodes)

    # Validieren, bevor geschrieben wird
    ET.fromstring(feed)

    with open(FEED_PATH, "w", encoding="utf-8") as f:
        f.write(feed)
    print(f"\n✓ {FEED_PATH} neu geschrieben mit {len(episodes)} Folgen.")


if __name__ == "__main__":
    main()
