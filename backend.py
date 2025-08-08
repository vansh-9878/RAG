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
from bs4 import BeautifulSoup
import json
import logging
load_dotenv()

def scrape_url(url):
    """
    Web scraper to get data from URL and return it
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Try to parse as JSON first
        try:
            json_data = response.json()
            return json_data
        except:
            # If not JSON, return text content
            soup = BeautifulSoup(response.text, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Error scraping URL {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error scraping URL {url}: {e}")
        return None

def check_content_for_embedding(content):
    """
    Check if content has sufficient data for embedding
    Raises exception if content is empty or insufficient
    """
    if not content:
        raise ValueError("Content is empty - no need to embed")
    
    if isinstance(content, str):
        # Remove whitespace and check length
        cleaned_content = content.strip()
        if len(cleaned_content) == 0:
            raise ValueError("Content is empty after cleaning - no need to embed")
        if len(cleaned_content) < 10:  # Minimum threshold
            raise ValueError("Content too short for meaningful embedding")
    
    elif isinstance(content, dict):
        # For JSON content, check if it has meaningful data
        if not any(content.values()):
            raise ValueError("JSON content has no meaningful values - no need to embed")
    
    return True

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
    print()
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
    fileName = filePath.split('.')[0].replace("%20"," ")
    print(fileName,filePath)
    if ".jpeg" in filePath:
        fileName+="_jpeg"
    elif ".png" in filePath:
        fileName+="_png"
    
    if fileName not in arr:
        # Check if this is a web scraping URL
        if "register.hackrx.in/utils/" in query.documents:
            try:
                content = scrape_url(query.documents)
                if content:
                    # Check if content is suitable for embedding
                    try:
                        check_content_for_embedding(content)
                        # Save scraped content
                        with open(f"{fileName}.txt", 'w', encoding='utf-8') as f:
                            if isinstance(content, dict):
                                f.write(json.dumps(content, indent=2))
                            else:
                                f.write(str(content))
                    except ValueError as e:
                        print(f"Skipping embedding for {query.documents}: {e}")
                        # Return empty response for empty content
                        return {"answers": ["Content is empty - no data available"] * len(query.questions)}
                else:
                    print(f"Failed to scrape content from {query.documents}")
                    return {"answers": ["Failed to retrieve content from URL"] * len(query.questions)}
            except Exception as e:
                print(f"Error processing URL {query.documents}: {e}")
                return {"answers": [f"Error processing URL: {str(e)}"] * len(query.questions)}
        else:
            # Regular file processing
            response = requests.get(query.documents)
            content_type = response.headers.get("Content-Type")

            if "pdf" in content_type:
                with open(f'{fileName}.pdf', "wb") as f:
                    f.write(response.content)
            elif "document" in content_type:
                doc = Document(io.BytesIO(response.content))
                text = "\n".join([para.text for para in doc.paragraphs])
                # Check content before saving
                try:
                    check_content_for_embedding(text)
                    with open(f"{fileName}.txt", 'w') as f:
                        f.write(text)
                except ValueError as e:
                    print(f"Skipping embedding for {fileName}: {e}")
                    return {"answers": ["Document is empty - no data available"] * len(query.questions)}
            else:
                # Check content before saving
                try:
                    check_content_for_embedding(response.content)
                    with open(f"{fileName}.txt", 'w') as f:
                        f.write(response.content.decode('utf-8', errors='ignore'))
                except ValueError as e:
                    print(f"Skipping embedding for {fileName}: {e}")
                    return {"answers": ["Content is empty - no data available"] * len(query.questions)}

        try:
            pdf_to_text(fileName)
        except Exception as e:
            print(f"Error in pdf_to_text for {fileName}: {e}")
            # Continue processing even if OCR fails
    
    try:
        index, texts = storeVectors(fileName)
        # Check if vectors were created successfully
        if not texts or len(texts) == 0:
            print(f"No text content found for {fileName} after vector processing")
            return {"answers": ["No meaningful content found in document"] * len(query.questions)}
    except Exception as e:
        print(f"Error in storeVectors for {fileName}: {e}")
        return {"answers": [f"Error processing document: {str(e)}"] * len(query.questions)}

    questions = query.questions
    total_questions = len(questions)
    print(total_questions)
    
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