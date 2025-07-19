#client.python
# How to Run:
#    First, run api.py and note the URL it prints (e.g., http://127.0.0.1:51234/api/v1/ordered-set).
#    In a new terminal window, run the client, passing that URL as an argument:
#    python client.py http://127.0.0.1:51234/api/v1/ordered-set
import requests
import sys
import json

def query_emoji_api(api_url: str):
    """
    Queries the local emoji API for a specific set of emojis.
    """
    # Define the query payload for the API
    query_payload = {
        "ordered_set_count": 128,
        "sets": ["core", "v12.0"] # Correctly requests the Unicode v12.0 set
    }

    print(f"Sending POST request to {api_url} with payload:")
    print(json.dumps(query_payload, indent=2))
    
    try:
        response = requests.post(api_url, json=query_payload)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        data = response.json()
        
        print("\n--- API Response ---")
        print(f"Successfully received {len(data)} emoji-index pairs.")
        
        # Print a sample of the response
        print("Sample (first 10):")
        for i in range(10):
            if str(i) in data:
                print(f"  Index {i}: {data[str(i)]}")

        # You can now use this ordered dictionary for your checksum autoencoder
        # For example, to get the emoji for index 5:
        # my_emoji = data['5']
    
    except requests.exceptions.HTTPError as http_err:
        print(f"\nHTTP Error occurred: {http_err}")
        # Try to print the JSON error response from the server
        try:
            print(f"Server response: {http_err.response.json()}")
        except json.JSONDecodeError:
            print(f"And the response body was: {http_err.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"\nError connecting to API: {e}")
    except json.JSONDecodeError:
        print("\nError: Failed to decode JSON from API response.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client.py <full_api_url>")
        print("Example: python client.py http://127.0.0.1:54321/api/v1/ordered-set")
        sys.exit(1)
    
    url = sys.argv[1]
    query_emoji_api(url)