from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent.ocrAgent import readPDF
from agent.search import uploadText
from agent.agent import start
import uvicorn
import requests

app=FastAPI()

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

@app.get("/")
def check():
    return{
        "status":"Status Running...."
    }
    
@app.post("/hackrx/run")
def getFile(query:input):
    filePath=query.documents.split('/')[-1].split('?')[0]
    fileName=filePath.split('.')[0]
    response=requests.get(query.documents)
    with open('policy.pdf',"wb") as f:
        f.write(response.content)
    readPDF(filePath,fileName)
    uploadText(fileName)
    answers=[]
    for question in query.questions:
        sample=start(question,fileName)
        answers.append(sample)
    return {    
        "answers":answers
    }

if __name__ == "__main__":
    uvicorn.run("backend:app", host="127.0.0.1", port=8080)