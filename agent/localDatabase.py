import faiss
from concurrent.futures import ThreadPoolExecutor
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from langchain_core.tools import tool
import numpy as np

model = SentenceTransformer("BAAI/bge-small-en-v1.5")
# model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
# model = SentenceTransformer("intfloat/e5-base-v2")
globalIndex=None
globalTexts=None


def load_text_chunks(filepath, chunk_size=800,stride=200):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    chunks = []

    for i in range(0, len(text), stride):
        chunk = text[i:i + chunk_size]
        if chunk:
            chunks.append(chunk)
    return chunks

def embed_in_batches(texts, model, batch_size=64, max_workers=4):
    embeddings = []

    def embed_batch(batch):
        return model.encode(batch, convert_to_numpy=True, normalize_embeddings=True)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            futures.append(executor.submit(embed_batch, batch))

        for future in tqdm(futures, desc="Embedding"):
            embeddings.append(future.result())

    return np.vstack(embeddings)

def create_faiss_index(embeddings):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  
    index.add(embeddings)
    return index


def search_faiss(index, query, texts,top_k=15):
    query_embedding = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    D, I = index.search(query_embedding, top_k)
    results = [(texts[i], float(D[0][j])) for j, i in enumerate(I[0])]
    return results


def storeVectors(fileName):
    texts = load_text_chunks(fileName+".txt")
    print(f"Loaded {len(texts)} chunks.")

    embeddings = embed_in_batches(texts, model, batch_size=64, max_workers=8)
    index = create_faiss_index(embeddings)
    global globalIndex,globalTexts
    globalTexts=texts
    globalIndex=index
    
@tool   
def search(query):
    """Search the document for the answer to the given query."""
    print("Tooooool")
    results = search_faiss(globalIndex, query, globalTexts)
    print("\nTop results:")
    for i, (text, score) in enumerate(results):
        print(f"\nRank {i+1} (Score: {score:.4f}):\n{text[:300]}...")
    return results
