import faiss,pickle
from concurrent.futures import ThreadPoolExecutor
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from langchain_core.tools import tool
# from localOCR import pdf_to_text
import numpy as np
import torch
import gc
import os

# Set PyTorch CUDA memory allocation configuration to avoid fragmentation
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'

# model = SentenceTransformer("BAAI/bge-small-en-v1.5")
# model = SentenceTransformer("all-MiniLM-L6-v2")
# Use GPU with memory optimization
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2", device='cuda')
# model = SentenceTransformer("intfloat/e5-base-v2")
globalIndex=None
globalTexts=None
arr=['Arogya%20Sanjeevani','Family%20Medicare','indian_constitution','principia_newton','Super_Splendor_(Feb_2023)','policy']


def load_text_chunks(filepath, chunk_size=800,stride=200):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    chunks = []

    for i in range(0, len(text), stride):
        chunk = text[i:i + chunk_size]
        if chunk:
            chunks.append(chunk)
    return chunks

def embed_in_batches(texts, model, batch_size=8, max_workers=2):
    embeddings = []

    def embed_batch(batch):
        # Clear GPU cache before processing batch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        batch_embeddings = model.encode(batch, convert_to_numpy=True, normalize_embeddings=True)
        
        # Clear GPU cache after processing batch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        return batch_embeddings

    # Process in smaller batches to avoid memory issues
    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding"):
        batch = texts[i:i + batch_size]
        embeddings.append(embed_batch(batch))
        
        # Force garbage collection
        gc.collect()

    return np.vstack(embeddings)

def create_faiss_index(embeddings):
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  
    index.add(embeddings)
    return index


def search_faiss(index, query, texts,top_k=25):
    query_embedding = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    D, I = index.search(query_embedding, top_k)
    results = [(texts[i], float(D[0][j])) for j, i in enumerate(I[0])]
    return results


def storeVectors(fileName):
    if any(fileName in item for item in arr):
        index = faiss.read_index(f"vector/{fileName}.faiss")
        with open(f"vector/{fileName}_texts.pkl", "rb") as f:
            texts = pickle.load(f)
    else:
        texts = load_text_chunks(fileName+".txt")
        print(f"Loaded {len(texts)} chunks.")

        embeddings = embed_in_batches(texts, model, batch_size=64, max_workers=8)
        index = create_faiss_index(embeddings)
        
        faiss.write_index(index, f"vector/{fileName}.faiss")

        with open(f"vector/{fileName}_texts.pkl", "wb") as f:
            pickle.dump(texts, f)
    

    global globalIndex,globalTexts

    globalTexts=texts
    globalIndex=index
    
@tool   
def search(query):
    """Search the document for the answer to the given query."""
    # print("Tooooool")
    results = search_faiss(globalIndex, query, globalTexts)
    # print("\nTop results:")
    # for i, (text, score) in enumerate(results):
        # print(f"\nRank {i+1} (Score: {score:.4f}):\n{text[:300]}...")
    return results

