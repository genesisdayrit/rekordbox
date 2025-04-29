#!/usr/bin/env python3
import os
import sys
from datetime import datetime
from typing import List, Dict

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Load vars from .env (and from real env as fallback)
load_dotenv()

# ——— Configuration ———
SCOPE = "user-library-read"   # permission to read your “Liked Songs”
DEFAULT_LIMIT = 20            # how many tracks to fetch by default
# ————————————————

def fetch_recent_liked(limit: int = DEFAULT_LIMIT) -> List[Dict]:
    """
    Fetches your most-recently saved tracks (newest first).
    Returns a list of dicts with title, artists, added_at (datetime), and spotify_url.
    """
    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            scope=SCOPE,
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
            cache_path=os.getenv("SPOTIFY_CACHE_PATH", ".cache"),
            show_dialog=False,
        )
    )

    results = sp.current_user_saved_tracks(limit=limit)
    parsed = []
    for item in results["items"][:limit]:
        added_at = datetime.fromisoformat(item["added_at"].replace("Z", "+00:00"))
        track = item["track"]
        artists = ", ".join(a["name"] for a in track["artists"])
        parsed.append({
            "title":       track["name"],
            "artists":     artists,
            "added_at":    added_at,
            "spotify_url": track["external_urls"]["spotify"],
        })
    return parsed

def main():
    # Ensure all required ENV vars are set
    for var in ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REDIRECT_URI"):
        if not os.getenv(var):
            sys.exit(f"Error: {var} is not set in your .env or environment.")

    # Parse optional command-line argument for how many tracks
    try:
        limit = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LIMIT
    except ValueError:
        sys.exit("Usage: python recent_likes.py [number_of_tracks]")

    recent = fetch_recent_liked(limit)
    if not recent:
        print("No saved tracks found.")
        return

    print(f"\nYour {len(recent)} most-recent liked songs:\n")
    for i, t in enumerate(recent, 1):
        date_str = t["added_at"].strftime("%Y-%m-%d %H:%M")
        print(f"{i:>2}. {t['title']} — {t['artists']} (added {date_str})")
    print()

if __name__ == "__main__":
    main()

