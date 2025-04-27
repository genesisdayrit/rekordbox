#!/usr/bin/env python3
import os
from datetime import datetime
import xml.etree.ElementTree as ET

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# ─── Configuration ──────────────────────────────────────────────────────────────

# Load environment variables
load_dotenv()
creds_file     = os.getenv("GDRIVE_CREDENTIALS_PATH")
spreadsheet_id = os.getenv("SPREADSHEET_ID")
XML_PATH = os.getenv("REKORDBOX_XML_PATH")

if not XML_PATH:
    raise RuntimeError("REKORDBOX_XML_PATH is not set in .env or environment")
if not creds_file:
    raise RuntimeError("GDRIVE_CREDENTIALS_PATH is not set in .env or environment")
if not spreadsheet_id:
    raise RuntimeError("SPREADSHEET_ID is not set in .env or environment")

# ─── Parse XML ─────────────────────────────────────────────────────────────────

print(f"Loading XML from {XML_PATH}…")
tree = ET.parse(XML_PATH)
root = tree.getroot()

# Define which TRACK attributes you want
FIELDS = [
    "TrackID", "Name", "Artist",
    "Album", "Genre", "TotalTime",
    "AverageBpm", "DateAdded",
    "PlayCount", "Rating", "Location"
]

rows = []
for track in root.findall(".//TRACK"):
    attrib = track.attrib
    # Pull out only the fields we care about; default to empty string
    row = [ attrib.get(f, "") for f in FIELDS ]
    rows.append(row)

print(f"Found {len(rows)} tracks.")

# ─── Authenticate with Google Sheets ───────────────────────────────────────────

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds  = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(spreadsheet_id)

# ─── Create / Replace Worksheet ─────────────────────────────────────────────────

# Use today's date as the sheet name, e.g. "2025-04-26"
sheet_name = datetime.now().strftime("%Y-%m-%d")
try:
    old_ws = spreadsheet.worksheet(sheet_name)
    spreadsheet.del_worksheet(old_ws)
    print(f"Deleted existing worksheet '{sheet_name}'.")
except gspread.exceptions.WorksheetNotFound:
    pass

ws = spreadsheet.add_worksheet(
    title=sheet_name,
    rows=len(rows)+1,
    cols=len(FIELDS)
)

# ─── Write Data ────────────────────────────────────────────────────────────────

header = FIELDS
payload = [header] + rows
ws.update("A1", payload)
print(f"Wrote {len(rows)} rows to '{sheet_name}'.")

print("Done! Your sheet is here:")
print(spreadsheet.url)

