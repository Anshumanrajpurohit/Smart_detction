import base64
import numpy as np


async def encode_embedding(embedding) -> str:
    return base64.b64encode(embedding.astype(np.float32).tobytes()).decode('utf-8')

async def decode_embedding(encoded_embedding: str) -> np.ndarray:
    decode_bytes = base64.b64decode(encoded_embedding.encode('utf-8'))
    return np.frombuffer(decode_bytes, dtype=np.float32)