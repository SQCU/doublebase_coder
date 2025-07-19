# src/doublebase_coder/cli.py

# We import the original logic and just call it.
# Note the use of relative imports (`.`) since they are in the same package.
import sys
from .scraper import scrape_and_process_emojis
from .api import main as run_api_logic

# These functions are the entry points registered in pyproject.toml
def run_scraper_entrypoint():
    """Entry point for the 'db-scrape' command."""
    print("--- Running DoubleBase Scraper via entry point ---")
    scrape_and_process_emojis()

def run_api_server_entrypoint():
    """Entry point for the 'db-api-server' command."""
    run_api_logic()

# --- START OF PATCH: Main execution block for direct calls ---
# This block runs when you execute `python -m doublebase_coder.cli server`
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("CLI Error: No command provided. Use 'server' or 'scrape'.", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    if command == "server":
        run_api_server_entrypoint()
    elif command == "scrape":
        run_scraper_entrypoint()
    else:
        print(f"CLI Error: Unknown command '{command}'.", file=sys.stderr)
        sys.exit(1)
# --- END OF PATCH ---