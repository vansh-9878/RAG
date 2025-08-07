from fastapi import FastAPI,Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent.localDatabase import storeVectors
from agent.agent import start
from agent.localOCR import pdf_to_text
from concurrent.futures import ThreadPoolExecutor, as_completed
import uvicorn,os,io
import requests
from docx import Document
from dotenv import load_dotenv
from datetime import datetime
import time
load_dotenv()

app=FastAPI()
bearer_scheme = HTTPBearer()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)


class input(BaseModel):
    documents:str
    questions:list

def chunk_list(lst, chunk_size):
    """Split a list into chunks of specified size"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    if token != os.getenv("TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
        )

@app.get("/hackrx/run")
def check():
    return{
        "status":"Status Running...."
    }
    
    
arr=os.listdir('./vector')
arr=[item.split(".")[0] for item in arr]
    
@app.post("/hackrx/run", dependencies=[Depends(verify_token)])
def getFile(query: input):
    # Record start time
    start_time = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Log request received
    print("=" * 80)
    print(f"REQUEST RECEIVED AT: {timestamp}")
    print(f"Documents: {query.documents}")
    print(f"Questions: {query.questions}")
    print("=" * 80)
    
    filePath = query.documents.split('/')[-1].split('?')[0]
    fileName = filePath.split('.')[0]
    
    if fileName not in arr:
        response = requests.get(query.documents)
        content_type = response.headers.get("Content-Type")

        if "pdf" in content_type:
            with open(f'{fileName}.pdf', "wb") as f:
                f.write(response.content)
        elif "document" in content_type:
            doc = Document(io.BytesIO(response.content))
            text = "\n".join([para.text for para in doc.paragraphs])
            with open(f"{fileName}.txt", 'w') as f:
                f.write(text)
        else:
            with open(f"{fileName}.txt", 'w') as f:
                f.write(response.content)

        pdf_to_text(fileName)
        
    index, texts = storeVectors(fileName)

    questions = query.questions
    total_questions = len(questions)
    
    # Initialize results array with None values
    results = [None] * total_questions
    
    # Create batches of 20 questions with their original indices
    batches = []
    for i in range(0, total_questions, 20):
        batch_end = min(i + 20, total_questions)
        batch_questions = questions[i:batch_end]
        batch_indices = list(range(i, batch_end))
        batches.append((batch_questions, batch_indices))

    # Process batches concurrently
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit all batch jobs
        future_to_batch = {}
        for batch_questions, batch_indices in batches:
            future = executor.submit(start, batch_questions, index, texts)
            future_to_batch[future] = (batch_questions, batch_indices)
        
        # Process completed futures
        for future in as_completed(future_to_batch):
            batch_questions, batch_indices = future_to_batch[future]
            
            try:
                batch_answers = future.result()
                
                # Validate the response
                if not isinstance(batch_answers, list):
                    batch_answers = [f"❌ Invalid response type: {type(batch_answers)}"] * len(batch_indices)
                elif len(batch_answers) != len(batch_indices):
                    # Pad or truncate to match expected length
                    if len(batch_answers) < len(batch_indices):
                        batch_answers.extend([f"❌ Missing answer"] * (len(batch_indices) - len(batch_answers)))
                    else:
                        batch_answers = batch_answers[:len(batch_indices)]
                
                # Assign answers to their correct positions in the results array
                for i, answer in enumerate(batch_answers):
                    original_index = batch_indices[i]
                    results[original_index] = answer
                    
            except Exception as e:
                error_msg = str(e)
                # Assign error messages to all questions in this batch
                for original_index in batch_indices:
                    results[original_index] = f"❌ Error: {error_msg}"
    
    # Final validation - ensure no None values remain
    for i, result in enumerate(results):
        if result is None:
            results[i] = "❌ No response received"
    
    response_data = {"answers": results}
    
    # Calculate time taken and log response sent
    end_time = time.time()
    time_taken = round(end_time - start_time, 2)
    response_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("RESPONSE SENT:")
    print(f"Response sent at: {response_timestamp}")
    print(f"Time taken: {time_taken} seconds")
    print(f"Answers: {results}")
    print("=" * 80)
    
    return response_data


if __name__ == "__main__":
    uvicorn.run("backend:app", host="127.0.0.1", port=8080)