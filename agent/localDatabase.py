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
import threading

# Set PyTorch CUDA memory allocation configuration to avoid fragmentation
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'

# model = SentenceTransformer("BAAI/bge-small-en-v1.5")
model = SentenceTransformer("all-MiniLM-L6-v2")
# Use GPU with memory optimization
# model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2", device='cuda')
# model = SentenceTransformer("intfloat/e5-base-v2")
globalIndex=None
globalTexts=None
search_lock = threading.Lock()

arr=os.listdir('./vector')
arr=[item.split(".")[0] for item in arr]
# print(arr)

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
    with search_lock:  # Add thread safety
        query_embedding = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        
        # Detailed debugging
        expected_dim = index.d
        actual_dim = query_embedding.shape[1]
        
        # print(f"Index dimension: {expected_dim}, Query embedding dimension: {actual_dim}")
        # print(f"Query embedding shape: {query_embedding.shape}")
        # print(f"Query embedding dtype: {query_embedding.dtype}")
        # print(f"Index type: {type(index)}")
        # print(f"Number of vectors in index: {index.ntotal}")
        
        if expected_dim != actual_dim:
            print(f"Dimension mismatch! Index expects {expected_dim} but query has {actual_dim}")
            return [("Error: Embedding dimension mismatch. Please regenerate the vector index.", 0.0)]
        
        try:
            D, I = index.search(query_embedding, top_k)
            print(f"Search successful, found {len(I[0])} results")
            results = [(texts[i], float(D[0][j])) for j, i in enumerate(I[0])]
            return results
        except Exception as e:
            print(f"FAISS search error: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            return [("Error during FAISS search", 0.0)]


def storeVectors(fileName):
    if fileName in arr:
        print(f"Loading pre-computed vectors for {fileName}")
        index = faiss.read_index(f"vector/{fileName}.faiss")
        with open(f"vector/{fileName}_texts.pkl", "rb") as f:
            texts = pickle.load(f)
        print(f"Loaded index with dimension: {index.d}")
    else:
        print(f"Creating new vectors for {fileName}")
        texts = load_text_chunks(fileName+".txt")
        print(f"Loaded {len(texts)} chunks.")

        embeddings = embed_in_batches(texts, model, batch_size=64, max_workers=8)
        index = create_faiss_index(embeddings)
        
        faiss.write_index(index, f"vector/{fileName}.faiss")

        with open(f"vector/{fileName}_texts.pkl", "wb") as f:
            pickle.dump(texts, f)
        print(f"Created new index with dimension: {index.d}")
    

    # global globalIndex,globalTexts

    # globalTexts=texts
    # globalIndex=index
    return index,texts
    
@tool
def search(query,index,texts):
    """Search the document for the answer to the given query."""
    # print("Tooooool")
    results = search_faiss(index, query, texts)
    # print("\nTop results:")
    # for i, (text, score) in enumerate(results):
        # print(f"\nRank {i+1} (Score: {score:.4f}):\n{text[:300]}...")
    return results

arr2 = [item for item in os.listdir('./') if item.endswith('.pdf')]
arr2 = [item[:-4] for item in arr2]
print(arr2)

for i in arr2:
    storeVectors(i)