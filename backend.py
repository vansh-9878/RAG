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
    
@app.post("/hackrx/run",dependencies=[Depends(verify_token)])
def getFile(query: input):
    filePath = query.documents.split('/')[-1].split('?')[0]
    fileName = filePath.split('.')[0]
    
    # Debug: Print the entire query object
    print(f"Received query: {query}")
    print(f"Questions received: {query.questions}")
    print(f"Number of questions: {len(query.questions) if query.questions else 0}")
    
    # Force flush the output
    import sys
    for question in query.questions:
        print(f"{fileName} {question}")
        sys.stdout.flush()  # Force immediate output
    
    response = requests.get(query.documents)
    content_type = response.headers.get("Content-Type")
        
    if "pdf" in content_type:
        with open(f'{fileName}.pdf', "wb") as f:
            f.write(response.content)
    elif "document" in content_type:
        doc = Document(io.BytesIO(response.content))
        text = "\n".join([para.text for para in doc.paragraphs])
        with open(f"{fileName}.txt",'w') as f:
            f.write(text)
    else:
        with open(f"{fileName}.txt",'w') as f:
            f.write(response.content)

    pdf_to_text(fileName)
    storeVectors(fileName)

    questions = query.questions
    results = [None] * len(questions)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(start, q): i
            for i, q in enumerate(questions)
        }

        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
                print('hii')
            except Exception as e:
                import traceback
                error_msg = traceback.format_exc()
                print(f"Error for question {questions[idx]}:\n{error_msg}")
                results[idx] = f"❌ Error: {str(e)}"
    # Print questions and answers before returning
    print("--- Questions and Answers ---")
    for q, a in zip(questions, results):
        print(f"Q: {q}\nA: {a}\n")
    print("----------------------------")
    import sys
    sys.stdout.flush()

    return {
        "answers": results
    }

if __name__ == "__main__":
    uvicorn.run("backend:app", host="127.0.0.1", port=8080)

