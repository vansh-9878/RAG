from fastapi import FastAPI,Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent.localDatabase import storeVectors
from agent.agent import start
from agent.localOCR import pdf_to_text
from concurrent.futures import ThreadPoolExecutor, as_completed
import uvicorn,os
import requests
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



@app.get("/")
def check():
    return{
        "status":"Status Running...."
    }
    
@app.post("/",dependencies=[Depends(verify_token)])
def getFile(query: input):
    filePath = query.documents.split('/')[-1].split('?')[0]
    fileName = filePath.split('.')[0]

    response = requests.get(query.documents)
    with open('policy.pdf', "wb") as f:
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
            except Exception as e:
                results[idx] = f"❌ Error: {str(e)}"

    return {
        "answers": results
    }

if __name__ == "__main__":
    uvicorn.run("backend:app", host="127.0.0.1", port=8080)