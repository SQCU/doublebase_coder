#api.py
# How to Run:
#    First, run api.py and note the URL it prints (e.g., http://127.0.0.1:51234/api/v1/ordered-set).
#    In a new terminal window, run the client, passing that URL as an argument:
#    python client.py http://127.0.0.1:51234/api/v1/ordered-set
import json
import socket
import os
import logging # <-- Import logging
import subprocess # <-- For running scraper
import sys        # <-- To find the correct python executable
from flask import Flask, request, jsonify

# --- Helper function to find a free port ---
def find_free_port():
    """
    Finds and returns an available TCP port on the local machine.
    This is done by binding a socket to port 0, which tells the OS to
    assign an ephemeral port. We then close the socket and return the port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

# --- Flask App Initialization ---
app = Flask(__name__)
emoji_data = {}
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EMOJI_DATA_FILENAME = "emoji_data.json"
EMOJI_DATA_PATH = os.path.join(SCRIPT_DIR, EMOJI_DATA_FILENAME)

# --- Patched Section: Set up logging ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE_PATH = os.path.join(SCRIPT_DIR, 'api.log')

# Configure logger to write to file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH), # Log to api.log
        logging.StreamHandler()             # Log to console (stdout)
    ]
)

def load_emoji_data():
    """Loads the emoji data from the JSON file into memory."""
    global emoji_data
    try:
        with open(EMOJI_DATA_PATH, 'r', encoding='utf-8') as f:
            emoji_data = json.load(f)
        logging.info(f"Successfully loaded {len(emoji_data)} emoji sets from '{EMOJI_DATA_PATH}'.")
    except FileNotFoundError:
        logging.error(f"'{EMOJI_DATA_PATH}' not found. Please run scraper.py first.")
        exit(1)
    except json.JSONDecodeError:
        logging.error(f"Could not decode JSON from '{EMOJI_DATA_PATH}'.")
        exit(1)

# Disable Flask's default verbose logging to avoid duplication
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

@app.route('/api/v1/ordered-set', methods=['POST'])
def get_ordered_emoji_set():
    """
    Handles POST requests to generate a server-ordered set of emojis.
    Expects JSON: {"ordered_set_count": int, "sets": ["set1", "set2"]}
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    count = data.get('ordered_set_count')
    set_names = data.get('sets')

    if not isinstance(count, int) or not isinstance(set_names, list):
        return jsonify({"error": "Invalid payload format. Required: {'ordered_set_count': int, 'sets': list}"}), 400
    
    combined_emojis = set()
    for name in set_names:
        if name in emoji_data:
            # Add emojis from the requested set to our master set
            combined_emojis.update(emoji_data[name])
        else:
            return jsonify({"error": f"Set '{name}' not found. Available sets: {list(emoji_data.keys())}"}), 400

    # The server determines the order by sorting the combined set.
    # This ensures a deterministic output for the same query.
    ordered_list = sorted(list(combined_emojis))
    # Truncate to the requested count
    final_list = ordered_list[:count]
    # Format the response as {index: emoji}
    response_payload = {str(i): emoji for i, emoji in enumerate(final_list)}

    return jsonify(response_payload)


# --- Main Application Logic ---
def main():
    """
    Main function for the API server. Implements the cold start logic
    to run the scraper if its data file is missing.
    """
    #
    # --- THIS IS THE API SERVER'S COLD START LOGIC ---
    #
    if not os.path.exists(EMOJI_DATA_PATH):
        logging.warning("Emoji data file not found. This is a cold start for the API.")
        logging.info("Attempting to run the scraper subprocess to generate data...")
        try:
            # --- START OF PATCH: Use the robust '-m' flag method ---
            subprocess.run(
                [sys.executable, "-m", "doublebase_coder.cli", "scrape"],
                check=True, capture_output=True, text=True
            )
            # --- END OF PATCH ---
            logging.info("Scraper subprocess completed successfully.")
        except subprocess.CalledProcessError as e:
            logging.error("FATAL: The scraper subprocess failed to run.", exc_info=True)
            logging.error(f"Scraper stderr:\n{e.stderr}")
            exit(1)
    else:
        logging.info("Emoji data file found. This is a warm start for the API.")

    # Now that data is guaranteed to exist, load it and start the server.
    load_emoji_data()

    # Disable Flask's default verbose logging to avoid duplication with our logger
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.WARNING)
    
    port = find_free_port()
    api_url = f"http://127.0.0.1:{port}/api/v1/ordered-set"
    
    logging.info("="*50)
    logging.info("DoubleBase API Server is starting...")
    # This specific log message is what our api_utils.py will search for
    logging.info(f"Send POST requests to: {api_url}")
    logging.info("="*50)
    
    app.run(host='127.0.0.1', port=port)

if __name__ == '__main__':
    main()