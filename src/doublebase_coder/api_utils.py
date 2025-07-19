import os
import re
from typing import Optional

def find_latest_api_url() -> Optional[str]:
    """
    Reads the 'api.log' file in the same directory to find the most
    recent URL the server was started on.

    Returns:
        The URL string if found, otherwise None.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file_path = os.path.join(script_dir, 'api.log')
    
    if not os.path.exists(log_file_path):
        return None

    # Regex to capture the specific URL from our log message
    url_pattern = re.compile(r"Send POST requests to: (http://127\.0\.0\.1:\d+/api/v1/ordered-set)")

    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            # Read lines and reverse them to find the latest entry first
            for line in reversed(f.readlines()):
                match = url_pattern.search(line)
                if match:
                    # Found the latest URL, return it
                    return match.group(1)
    except IOError:
        return None # Failed to read file

    return None # No URL found in the entire file