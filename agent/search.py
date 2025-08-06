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

model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")  

from concurrent.futures import ThreadPoolExecutor

def uploadText(fileName: str, batch_size=50):
    with open(f"{fileName}.txt", 'r', encoding='utf-8') as f:
        text = f.read().strip().replace("\n"," ")
    if not text:
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=100)
    chunks = splitter.split_text(text)

    def chunk_batches(lst, size):
        for i in range(0, len(lst), size):
            yield lst[i:i + size]

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for batch_id, batch in enumerate(chunk_batches(chunks, batch_size)):
            embeddings = model.encode(batch, batch_size=32)  # Fast per batch
            vectors = [
                {
                    'id': f"{fileName}-{batch_id * batch_size + i}",
                    'values': emb.tolist(),
                    'metadata': {'text': chunk}
                }
                for i, (chunk, emb) in enumerate(zip(batch, embeddings))
            ]
            futures.append(executor.submit(index.upsert, vectors=vectors, namespace=fileName))

        for i, f in enumerate(futures):
            f.result()

@tool
def searchDocument(query:str,filename:str)->list:
    """Search the document for the answer to the given query."""
    query_embedding = model.encode(query).tolist()
    
    results = index.query(
        vector=query_embedding,
        top_k=3,
        include_metadata=True,
        namespace=filename
    )
    
    return results['matches']

# searchDocument.invoke({"query":"What is the waiting period for pre-existing diseases (PED) to be covered?","filename":"policy"})