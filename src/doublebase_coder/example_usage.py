#example_usage.py
#~~python doublebasecoder\example_usage.py >> doublebasecoder\example_usage.txt 2>&1~~
#python example_usage.py >> example_usage.txt 2>&1
import asyncio
import os
from doublebase_coder import cold_setup, warm_setup, dbaser

# Define a path for our application's central, user-managed cache file.
# This is the recommended approach for any serious application.
CENTRAL_CACHE_PATH = "my_app_decoder_configs.json"

async def main():
    """Demonstrates the new, responsible caching and setup workflow."""

    print("="*60)
    print("SCENARIO 1: First-time run with an explicit, central cache file.")
    print("="*60)

    # --- STEP 1: Try to load from our central cache ---
    # On the first run, this will fail because the file doesn't exist yet.
    dbase_configs = warm_setup(cache_path=CENTRAL_CACHE_PATH)

    # --- STEP 2: If cache fails, run cold setup, pointing to our central cache ---
    if dbase_configs is None:
        print(f"Cache '{CENTRAL_CACHE_PATH}' not found. Performing initial cold setup...")
        # We only need two bases for now. This will create and populate the central cache file.
        dbase_configs = await cold_setup(bases=[256, 1024], cache_path=CENTRAL_CACHE_PATH)
    
    if not dbase_configs:
        print("\nSetup failed. Exiting."); return

    # --- STEP 3: Use an encoder from the loaded/created configuration ---
    encode_256, decode_256 = dbaser(dbase_configs['256'])
    checksum = os.urandom(16) # Generate a random 128-bit checksum for testing
    dec, emo = encode_256(checksum)
    print(f"\nEncoded with base 256: {dec} | {emo}")
    assert decode_256(dec, emo) == checksum, "Verification Failed!"
    print("Verification successful.")


    print("\n\n" + "="*60)
    print("SCENARIO 2: Updating the central cache with a new mapping.")
    print("="*60)

    # We now decide our application also needs a 2048-emoji base.
    # cold_setup is smart: it will load our existing cache and only fetch the missing piece.
    print(f"Calling cold_setup again to add base 2048 to '{CENTRAL_CACHE_PATH}'...")
    dbase_configs = await cold_setup(bases=[256, 1024, 2048], cache_path=CENTRAL_CACHE_PATH)
    
    if dbase_configs and '2048' in dbase_configs:
        print("\nSuccessfully updated cache with base 2048 configuration.")
        # We could now use dbaser(dbase_configs['2048']) if we wanted.
    else:
        print("\nFailed to update cache.")


    print("\n\n" + "="*60)
    print("SCENARIO 3: Running without a path (Safety-Net Behavior).")
    print("="*60)
    
    # This simulates a quick test script or a user who doesn't specify a cache path.
    # The library creates a local, uniquely named file to prevent data loss
    # and tells the user how to find and reuse it.
    print("Calling cold_setup with no 'cache_path' argument...")
    unmanaged_configs = await cold_setup(bases=[512]) # Just need one new base
    
    if unmanaged_configs:
        print("\nSafety-net cache and in-memory object created successfully.")


if __name__ == "__main__":
    # This setup block ensures the demonstration is clean every time you run it.
    print("--- Preparing for demonstration by cleaning up old cache files... ---")
    if os.path.exists(CENTRAL_CACHE_PATH):
        os.remove(CENTRAL_CACHE_PATH)
    for f in os.listdir("."):
        if f.startswith("dbase_cache_") and f.endswith(".json"):
            os.remove(f)
    print("--- Cleanup complete. Starting main demo. ---\n")

    asyncio.run(main())