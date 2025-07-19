#scraper.py
import requests
import json
import os
import re
from collections import defaultdict

# --- Configuration ---
# Using Unicode 13.0 data as a reliable source covering the 2020 timeframe.
EMOJI_DATA_URL = "https://unicode.org/Public/emoji/13.0/emoji-test.txt"

# --- Patched Section: Use the script's directory for the output file ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILENAME = "emoji_data.json"
OUTPUT_FILE_PATH = os.path.join(SCRIPT_DIR, OUTPUT_FILENAME)

# Define the versions for our sets
CORE_VERSIONS = {'11.0'}
EXTENDED_VERSIONS = {'11.0', '12.0', '12.1', '13.0'} # Covers 2018-2020 releases

def scrape_and_process_emojis():
    """
    Scrapes emoji data, categorizes emojis by version, and saves them
    into structured sets in a JSON file.
    """
    print(f"Fetching emoji data from {EMOJI_DATA_URL}...")
    try:
        response = requests.get(EMOJI_DATA_URL)
        response.raise_for_status() # Raise an exception for bad status codes
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return

    print("Processing data...")
    # This regex captures the emoji character and its version number from lines like:
    # 1F9A0 ; fully-qualified # 🦠 E11.0 microbe
    emoji_version_pattern = re.compile(r'fully-qualified\s+#\s+(.*?)\s+E(\d+\.\d+)')
    
    emojis_by_version = defaultdict(list)

    for line in response.text.splitlines():
        if line.startswith('#') or not line.strip():
            continue # Skip comments and empty lines
        
        match = emoji_version_pattern.search(line)
        if match:
            emoji_char = match.group(1).strip()
            version = match.group(2)
            emojis_by_version[version].append(emoji_char)

    # --- Build the final data structure ---
    all_sets = {f"v{v}": sorted(list(set(emojis))) for v, emojis in emojis_by_version.items()}

    # Create the 'core' set (Unicode 11.0)
    core_set_emojis = []
    for version in CORE_VERSIONS:
        core_set_emojis.extend(all_sets.get(f"v{version}", []))
    all_sets['core'] = sorted(list(set(core_set_emojis)))

    # Create the 'extended' set (Unicode 11.0 - 13.0)
    extended_set_emojis = []
    for version in EXTENDED_VERSIONS:
        extended_set_emojis.extend(all_sets.get(f"v{version}", []))
    all_sets['extended'] = sorted(list(set(extended_set_emojis)))

    # --- Save to file ---
    try:
        with open(OUTPUT_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(all_sets, f, ensure_ascii=False, indent=2)
        print(f"\nSuccessfully created '{OUTPUT_FILE_PATH}'")
        print(f"Core set contains {len(all_sets['core'])} emojis.")
        print(f"Extended set contains {len(all_sets['extended'])} emojis.")
    except IOError as e:
        print(f"Error writing to file: {e}")


if __name__ == "__main__":
    scrape_and_process_emojis()