#doublebase_tool.py
#python doublebasecoder\doublebase_tool.py 256 DEADBEEFDEADBEEFBDEADBEEF4206969 > doublebasecoder\doublebase_tool.txt 2>&1
import math
import sys
import json
import asyncio
import httpx  # Using async-native httpx
import regex  # Using grapheme-group aware emoji sequence indexing
from typing import List, Tuple, Dict

# NEW: Import our URL discovery utility
from api_utils import find_latest_api_url

# (The HybridBaseEncoder class remains exactly the same as the previous version)
class HybridBaseEncoder:
    # ... (no changes needed here, copy from previous response) ...
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
        self.decimal_capacity = self.decimal_base ** self.half_N
        self.emoji_capacity = self.emoji_count ** self.half_N
        self.total_capacity = self.decimal_capacity * self.emoji_capacity
        print(f"Encoder Initialized: Using {self.emoji_count} emojis.")
        print(f"  - Optimal total length (N): {self.N} ({self.half_N} decimals, {self.half_N} emojis)")
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
        if len(decimal_digits) != self.half_N or len(emoji_indices) != self.half_N: raise ValueError(f"Invalid input length")
        val = 0
        for digit in decimal_digits: val = val * self.decimal_base + digit
        for index in emoji_indices: val = val * self.emoji_count + index
        return val
    def encode(self, data_bytes: bytes) -> Tuple[str, str]:
        checksum_int = int.from_bytes(data_bytes, 'big')
        decimal_digits, emoji_indices = self._encode_to_indices(checksum_int)
        decimal_str = "".join(map(str, decimal_digits))
        emoji_str = "".join([self.emoji_map[str(i)] for i in emoji_indices])
        return decimal_str, emoji_str
    def decode(self, decimal_str: str, emoji_str: str) -> bytes:
        decimal_digits = [int(d) for d in decimal_str]
        # The special regex `\X` matches a single Unicode grapheme cluster.
        # This correctly splits "🤏🏾" as one item instead of two.
        graphemes = regex.findall(r'\X', emoji_str)
        emoji_indices = [int(self.reverse_emoji_map[emo]) for emo in graphemes]
        checksum_int = self._decode_from_indices(decimal_digits, emoji_indices)
        return checksum_int.to_bytes(16, 'big')

async def get_emoji_map_from_api_async(api_url: str, count: int, sets: list) -> Dict[str, str]:
    """
    Asynchronously queries the local emoji API. Exits on failure.
    """
    payload = {"ordered_set_count": count, "sets": sets}
    print(f"--> Querying API at {api_url} for {count} emojis from sets {sets}...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, json=payload, timeout=5.0)
            response.raise_for_status()
            emoji_map = response.json()
            if len(emoji_map) < count:
                print(f"Warning: Requested {count}, but API only returned {len(emoji_map)}.")
            print(f"--> Successfully received map with {len(emoji_map)} emojis.")
            return emoji_map
        except httpx.RequestError as e:
            print(f"\nFATAL: Could not connect to API at {e.request.url}.")
            print("Is the api.py server running?")
            sys.exit(1)

# NEW: Main function is now async
async def main():
    try:
        emoji_set_size = int(sys.argv[1])
        hex_checksum = sys.argv[2]
        if len(hex_checksum.replace("0x", "")) != 32:
            raise ValueError("Hex checksum must be 32 characters (128 bits).")
        input_bytes = bytes.fromhex(hex_checksum.replace("0x", ""))
    except (IndexError, ValueError) as e:
        # ... (usage instructions are the same) ...
        print("--- Hybrid Base Encoder Tool ---")
        print("\nUsage: python doublebase_tool.py <emoji_count> <32-char_hex_checksum>")
        sys.exit(1)
        
    # 1. Automatically find the API URL
    api_url = find_latest_api_url()
    if not api_url:
        print("\nFATAL: Could not find a running API server.")
        print("Please run 'python api.py' in another terminal first.")
        sys.exit(1)

    # 2. Get the emoji set from our local API asynchronously
    emoji_mapping = await get_emoji_map_from_api_async(api_url, emoji_set_size, ["core", "extended"])
    
    # 3. Initialize the encoder
    encoder = HybridBaseEncoder(emoji_mapping)
    
    # ... (rest of the logic is the same) ...
    print("\n--- ENCODING ---")
    print(f"Original Hex:   0x{input_bytes.hex()}")
    decimal_part, emoji_part = encoder.encode(input_bytes)
    print(f"Encoded Decimal: {decimal_part}")
    print(f"Encoded Emoji:   {emoji_part}")
    
    print("\n--- DECODING & VERIFICATION ---")
    decoded_bytes = encoder.decode(decimal_part, emoji_part)
    print(f"Decoded Hex:    0x{decoded_bytes.hex()}")
    print(f"Verification OK: {input_bytes == decoded_bytes}")

if __name__ == "__main__":
    # NEW: Run the async main function
    asyncio.run(main())