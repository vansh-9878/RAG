from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
import os
from langchain_core.tools import tool
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
load_dotenv()


pc=Pinecone(api_key=os.getenv("PINECONE_API"))

index = pc.Index(name="ragsearch",host="https://ragsearch-e785njk.svc.aped-4627-b74a.pinecone.io")

model = SentenceTransformer("all-MiniLM-L6-v2")  

from concurrent.futures import ThreadPoolExecutor

def uploadText(fileName: str, batch_size=50):
    with open(f"{fileName}.txt", 'r', encoding='utf-8') as f:
        text = f.read().strip()

    if not text:
        print("❌ File is empty.")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_text(text)

    embeddings = model.encode(chunks, batch_size=32, show_progress_bar=True)

    vectors = [
        {
            'id': f"{fileName}-{i}",
            'values': embedding.tolist(),
            'metadata': {'text': chunk}
        }
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]

    print(f"🚀 Upserting {len(vectors)} vectors in batches of {batch_size}...")

    def upsert_batch(batch):
        index.upsert(vectors=batch, namespace=fileName)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            futures.append(executor.submit(upsert_batch, batch))

        for i, f in enumerate(futures):
            f.result()  # Block for each future to complete
            print(f"✅ Uploaded batch {i + 1}")

    print(f"✅ All {len(vectors)} vectors uploaded to namespace '{fileName}'")



@tool
def searchDocument(query:str,filename:str)->list:
    """Search the document for the answer to the given query."""
    print("Tooooool")
    query_embedding = model.encode(query).tolist()
    
    results = index.query(
        vector=query_embedding,
        top_k=2,
        include_metadata=True,
        namespace=filename
    )
    
    for match in results['matches']:
        print(f"Score: {match['score']:.4f}")
        print(f"Text: {match['metadata']['text']}\n")
    return results['matches']
