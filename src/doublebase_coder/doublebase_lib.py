import json
import asyncio
import os
import httpx
import regex
import subprocess
import sys
import time
import logging
import uuid
from typing import List, Tuple, Dict, Optional, Callable

# Use a relative import now that it's in a package
from .api_utils import find_latest_api_url

DEFAULT_CACHE_FILENAME = "dbase_cache.json"

# ==============================================================================
# SECTION 1: INTERNAL CORE LOGIC (The Encoder Class)
# ==============================================================================

class _HybridBaseEncoder:
    """Internal class to handle the encoding/decoding mathematics."""
    def __init__(self, emoji_map: Dict[str, str]):
        self.emoji_map = emoji_map
        self.reverse_emoji_map = {v: k for k, v in emoji_map.items()}
        self.emoji_count = len(self.emoji_map)
        if self.emoji_count == 0: raise ValueError("Emoji map cannot be empty.")
        self.decimal_base = 10
        self.input_bits = 128
        self.max_input_value = 2**self.input_bits - 1
        self.N = self._find_minimum_N()
        self.half_N = self.N // 2
    def _find_minimum_N(self) -> int:
        N = 2
        while True:
            half = N // 2
            if half == 0: N += 2; continue
            capacity = (self.decimal_base ** half) * (self.emoji_count ** half)
            if capacity >= 2**self.input_bits: return N
            N += 2
    def _encode_to_indices(self, checksum_int: int) -> Tuple[List[int], List[int]]:
        if checksum_int > self.max_input_value: raise ValueError(f"Input {checksum_int} exceeds 128-bit range")
        decs, emos = [], []
        temp_val = checksum_int
        for _ in range(self.half_N):
            emos.insert(0, temp_val % self.emoji_count)
            temp_val //= self.emoji_count
        for _ in range(self.half_N):
            decs.insert(0, temp_val % self.decimal_base)
            temp_val //= self.decimal_base
        return decs, emos
    def _decode_from_indices(self, decimal_digits: List[int], emoji_indices: List[int]) -> int:
        val = 0
        for digit in decimal_digits: val = val * self.decimal_base + digit
        for index in emoji_indices: val = val * self.emoji_count + index
        return val
    def encode(self, data_bytes: bytes) -> Tuple[str, str]:
        checksum_int = int.from_bytes(data_bytes, 'big')
        decimal_digits, emoji_indices = self._encode_to_indices(checksum_int)
        decimal_str = "".join(map(str, decimal_digits)).zfill(self.half_N)
        emoji_str = "".join([self.emoji_map[str(i)] for i in emoji_indices])
        return decimal_str, emoji_str
    def decode(self, decimal_str: str, emoji_str: str) -> bytes:
        decimal_digits = [int(d) for d in decimal_str]
        graphemes = regex.findall(r'\X', emoji_str)
        emoji_indices = [int(self.reverse_emoji_map[emo]) for emo in graphemes]
        checksum_int = self._decode_from_indices(decimal_digits, emoji_indices)
        return checksum_int.to_bytes(16, 'big', signed=False)

# ==============================================================================
# SECTION 2: PUBLIC-FACING LIBRARY FUNCTIONS
# ==============================================================================

async def _get_map_async(client: httpx.AsyncClient, api_url: str, count: int) -> Dict[str, str]:
    """Helper coroutine to fetch one emoji map."""
    payload = {"ordered_set_count": count, "sets": ["core", "extended"]}
    response = await client.post(api_url, json=payload, timeout=10.0)
    response.raise_for_status()
    return response.json()

def warm_setup(cache_path: str) -> Optional[dict]:
    """
    Performs fast setup by loading configurations from a user-specified cache file.
    """
    if not os.path.exists(cache_path):
        return None
    print(f"--- Running Warm Setup (loading from '{cache_path}') ---")
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        logging.error(f"Could not read or parse cache file: {cache_path}", exc_info=True)
        return None

async def cold_setup(bases: List[int], cache_path: Optional[str] = None) -> Optional[dict]:
    """
    Establishes and persists emoji mappings. Manages its own dependencies.
    """
    print("--- Running Cold Setup ---")
    
    is_default_path = False
    if cache_path:
        target_cache_path = cache_path
    else:
        is_default_path = True
        default_filename = f"dbase_cache_{uuid.uuid4().hex[:8]}.json"
        target_cache_path = os.path.join(os.getcwd(), default_filename)
        print(f"  No cache_path provided. Using default safety-net path: {target_cache_path}")

    existing_configs = warm_setup(target_cache_path) if os.path.exists(target_cache_path) else {}
    if existing_configs is None: existing_configs = {}

    bases_to_fetch = [b for b in bases if str(b) not in existing_configs]
    if not bases_to_fetch:
        print("  All requested bases are already present in the cache. No API call needed.")
        return existing_configs

    print(f"  Cache is missing mappings for bases: {bases_to_fetch}. API query required.")

    api_process = None
    final_api_url = None
    
    candidate_url = find_latest_api_url()
    if candidate_url:
        print(f"  Log file found candidate server: {candidate_url}")
        print("  Verifying if it's responsive...")
        try:
            async with httpx.AsyncClient() as client:
                await client.post(candidate_url, json={"ordered_set_count": 1, "sets": ["core"]}, timeout=2.0)
            final_api_url = candidate_url
            print("  Verification successful. Using existing server.")
        # --- Start of Local Change ---
        # The exception list is expanded to include the specific timeout error.
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
        # --- End of Local Change ---
            print("  Verification failed. Server is not running at that address (stale log).")
            
    if final_api_url is None:
        print("  No active API server found or verified. Starting a temporary one...")
        try:
            api_process = subprocess.Popen(
                [sys.executable, "-m", "doublebase_coder.cli", "server"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            for _ in range(30):
                time.sleep(0.5)
                newly_found_url = find_latest_api_url()
                if newly_found_url and newly_found_url != candidate_url:
                    final_api_url = newly_found_url
                    break
            if not final_api_url:
                raise RuntimeError("Temporary API server started but failed to log its URL in time.")
            print(f"  Temporary server started and located at: {final_api_url}")
        except Exception:
            logging.error("Failed to start and manage temporary API server.", exc_info=True)
            if api_process: api_process.terminate()
            return None

    try:
        newly_fetched_configs = {}
        async with httpx.AsyncClient() as client:
            tasks = [_get_map_async(client, final_api_url, b) for b in bases_to_fetch]
            results = await asyncio.gather(*tasks)
            for base, emoji_map in zip(bases_to_fetch, results):
                newly_fetched_configs[str(base)] = {"emoji_count": len(emoji_map), "emoji_map": emoji_map}
        
        final_configs = {**existing_configs, **newly_fetched_configs}
        with open(target_cache_path, 'w', encoding='utf-8') as f:
            json.dump(final_configs, f, ensure_ascii=False, indent=2)
        print(f"--- Configuration successfully saved to '{target_cache_path}' ---")

        if is_default_path:
            print("\n  [RECOMMENDATION] To reuse this mapping, pass its path in future calls:")
            print(f"  > warm_setup(cache_path='{os.path.abspath(target_cache_path)}')")
        return final_configs
    except Exception:
        logging.error("Failed to query API and build cache.", exc_info=True)
        return None
    finally:
        if api_process:
            print("  Shutting down temporary API server...")
            api_process.terminate()
            api_process.wait(timeout=5)

def dbaser(config: dict) -> Tuple[Callable, Callable]:
    """
    A factory that takes a specific configuration and returns tailored
    encoding and decoding functions.
    """
    if not config or "emoji_map" not in config:
        raise ValueError("Invalid configuration passed to dbaser. Expected a dict with 'emoji_map'.")
    encoder_instance = _HybridBaseEncoder(config['emoji_map'])
    def dbase_encode(data_bytes: bytes) -> Tuple[str, str]:
        return encoder_instance.encode(data_bytes)
    def dbase_decode(decimal_str: str, emoji_str: str) -> bytes:
        return encoder_instance.decode(decimal_str, emoji_str)
    return dbase_encode, dbase_decode