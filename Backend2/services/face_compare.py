import numpy as np
from numpy import dot
from numpy.linalg import norm

threshold = 0.6  

async def cosine_similarity(emb1, emb2):
    return dot(emb1, emb2) / (norm(emb1) * norm(emb2))

async def face_compare(emb1, emb2):
    similarity = await cosine_similarity(emb1, emb2)
    return similarity > threshold