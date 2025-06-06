#!/usr/bin/env python3
import os
import re
import sys
from datetime import datetime
from typing import List, Dict, Tuple

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables
load_dotenv()

# ─── Configuration ──────────────────────────────────────────────────────────────

# Spotify configuration
SCOPE = "playlist-read-private playlist-read-collaborative"

# Google Sheets configuration
creds_file = os.getenv("GDRIVE_CREDENTIALS_PATH")
spreadsheet_id = os.getenv("SPREADSHEET_ID")

# ─── Helper Functions ───────────────────────────────────────────────────────────

def extract_playlist_id(playlist_url: str) -> str:
    """
    Extract playlist ID from Spotify URL.
    Supports various formats like:
    - https://open.spotify.com/playlist/37i9dQZF1DX0XUsuxWHRQd
    - spotify:playlist:37i9dQZF1DX0XUsuxWHRQd
    """
    # Remove query parameters and fragments
    playlist_url = playlist_url.split('?')[0].split('#')[0]
    
    # Try different patterns
    patterns = [
        r'playlist/([a-zA-Z0-9]+)',
        r'playlist:([a-zA-Z0-9]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, playlist_url)
        if match:
            return match.group(1)
    
    raise ValueError(f"Could not extract playlist ID from URL: {playlist_url}")

def get_playlist_data(playlist_url: str) -> Tuple[str, List[Dict]]:
    """
    Fetch playlist name and tracks from Spotify.
    Returns (playlist_name, list_of_tracks)
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
    
    playlist_id = extract_playlist_id(playlist_url)
    
    # Get playlist info
    playlist = sp.playlist(playlist_id)
    playlist_name = playlist['name']
    
    # Get all tracks (handle pagination)
    tracks = []
    results = sp.playlist_tracks(playlist_id)
    
    while results:
        for item in results['items']:
            if item['track'] and item['track']['name']:  # Skip None tracks
                track = item['track']
                artists = ", ".join(a["name"] for a in track["artists"])
                song_info = f"{track['name']} - {artists}"
                
                tracks.append({
                    "song": song_info,
                    "spotify_url": track["external_urls"]["spotify"]
                })
        
        # Check if there are more pages
        if results['next']:
            results = sp.next(results)
        else:
            break
    
    return playlist_name, tracks

def create_sheets_worksheet(playlist_name: str, tracks: List[Dict]) -> None:
    """
    Create a new worksheet in Google Sheets with the playlist data.
    """
    # Authenticate with Google Sheets
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(spreadsheet_id)
    
    # Clean playlist name for sheet name (remove invalid characters)
    sheet_name = re.sub(r'[^\w\s-]', '', playlist_name).strip()
    if len(sheet_name) > 100:  # Google Sheets limit
        sheet_name = sheet_name[:100]
    
    # Delete existing worksheet if it exists
    try:
        old_ws = spreadsheet.worksheet(sheet_name)
        spreadsheet.del_worksheet(old_ws)
        print(f"Deleted existing worksheet '{sheet_name}'.")
    except gspread.exceptions.WorksheetNotFound:
        pass
    
    # Create new worksheet
    ws = spreadsheet.add_worksheet(
        title=sheet_name,
        rows=len(tracks) + 1,  # +1 for header
        cols=3
    )
    
    # Prepare data
    header = ["Track #", "Song", "Spotify Link"]
    rows = [header]
    
    for i, track in enumerate(tracks, 1):
        rows.append([
            i,
            track["song"],
            track["spotify_url"]
        ])
    
    # Write data to sheet
    ws.update("A1", rows)
    print(f"Created worksheet '{sheet_name}' with {len(tracks)} tracks.")
    print(f"Spreadsheet URL: {spreadsheet.url}")

def main():
    # Check required environment variables
    required_vars = [
        "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REDIRECT_URI",
        "GDRIVE_CREDENTIALS_PATH", "SPREADSHEET_ID"
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            sys.exit(f"Error: {var} is not set in your .env or environment.")
    
    # Get playlist URL from user
    playlist_url = input("Enter the Spotify playlist URL: ").strip()
    
    if not playlist_url:
        sys.exit("Error: No playlist URL provided.")
    
    try:
        print("Fetching playlist data from Spotify...")
        playlist_name, tracks = get_playlist_data(playlist_url)
        
        if not tracks:
            print("No tracks found in the playlist.")
            return
        
        print(f"Found playlist '{playlist_name}' with {len(tracks)} tracks.")
        
        print("Creating Google Sheets worksheet...")
        create_sheets_worksheet(playlist_name, tracks)
        
        print("Done!")
        
    except Exception as e:
        sys.exit(f"Error: {e}")

if __name__ == "__main__":
    main() 