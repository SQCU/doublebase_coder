#example_usage.py
#~~python doublebasecoder\example_usage.py >> doublebasecoder\example_usage.txt 2>&1~~
#python src\doublebase_coder\example_usage.py >> src\doublebase_coder\example_usage.txt 2>&1
import asyncio
from .doublebase_lib import cold_setup, warm_setup, dbaser

async def main():
    """Demonstrates the intended workflow of the doublebase_lib."""

    # Define the emoji bases we are interested in for our application
    DESIRED_BASES = [256, 1024, 2048]
    
    # --- STEP 1: Try to load from cache ---
    dbase_configs = warm_setup()

    # --- STEP 2: If cache fails, run the one-time cold setup ---
    if dbase_configs is None:
        print("Cache not found or invalid. Performing initial cold setup...")
        dbase_configs = await cold_setup(DESIRED_BASES)

    # --- STEP 3: Check if setup was successful ---
    if dbase_configs is None:
        print("\nSetup failed. Please ensure the API server is running and accessible.")
        return

    # --- STEP 4: Get encoder/decoder functions for a specific base ---
    # We want to work with a 256-emoji alphabet for this example.
    target_base = '256'
    if target_base not in dbase_configs:
        print(f"Error: Configuration for base '{target_base}' not found in the cache.")
        return

    print(f"\n--- Preparing to use base {target_base} ---")
    try:
        # Get the two functions from our factory
        encode_checksum, decode_checksum = dbaser(dbase_configs[target_base])
    except ValueError as e:
        print(f"Failed to initialize dbaser: {e}")
        return

    # --- STEP 5: Use the functions ---
    print("--- Running example encoding/decoding ---")
    
    # A sample 128-bit checksum
    original_checksum_bytes = bytes.fromhex("a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6")
    print(f"Original Checksum:  {original_checksum_bytes.hex()}")

    # Encode it
    decimal_part, emoji_part = encode_checksum(original_checksum_bytes)
    print(f"Encoded (Decimal):  {decimal_part}")
    print(f"Encoded (Emoji):    {emoji_part}")
    
    # Decode it
    decoded_checksum_bytes = decode_checksum(decimal_part, emoji_part)
    print(f"Decoded Checksum:   {decoded_checksum_bytes.hex()}")

    # Verify
    print(f"\nVerification successful: {original_checksum_bytes == decoded_checksum_bytes}")


if __name__ == "__main__":
    # Ensure api.py is running in another terminal before executing this.
    asyncio.run(main())