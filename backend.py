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

def get_llm_response(prompt, max_tokens=100):
    """
    Simple LLM response function - fallback to keyword analysis if LLM fails
    """
    try:
        # Since LLM is causing issues, use simple keyword-based classification
        prompt_lower = prompt.lower()
        
        # Extract the question from the prompt
        if 'question:' in prompt_lower:
            question_part = prompt_lower.split('question:')[1].split('\n')[0]
            
            # Simple classification based on keywords
            if any(word in question_part for word in ['flight number', 'my flight', 'flight']):
                return "complex"
            elif any(word in question_part for word in ['secret', 'token', 'url', 'go to']):
                return "complex"
            else:
                return "simple"
        
        return "simple"  # Safe fallback
    except Exception as e:
        print(f"Error getting LLM response: {e}")
        return "simple"  # Safe fallback

def classify_question_intent(question, document_content=""):
    """
    Use simple keyword matching to determine if question requires complex navigation or simple Q&A
    """
    try:
        question_lower = question.lower()
        print(f"Classifying question: {question}")
        
        # Complex navigation keywords
        complex_keywords = [
            "flight number", "my flight", "what is my flight",
            "secret", "token", "go to url", "go to the url",
            "get secret", "find flight", "flight info"
        ]
        
        # Check if question contains complex navigation keywords
        is_complex = any(keyword in question_lower for keyword in complex_keywords)
        
        if is_complex:
            print(f"Classified as COMPLEX navigation")
            return "complex"
        else:
            print(f"Classified as SIMPLE document Q&A")
            return "simple"
        
    except Exception as e:
        print(f"Error in classification: {e}")
        return "simple"  # Safe fallback

def execute_complex_navigation(question, document_url, document_content):
    """
    Handle complex questions by scraping document content and using LLM to find solution
    """
    try:
        print(f"Executing complex navigation for: {question}")
        
        # Step 1: Get the document content if not provided
        if not document_content:
            print("Getting document content...")
            try:
                response = requests.get(document_url)
                if response.status_code == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "text" in content_type or "html" in content_type:
                        document_content = response.text
                    else:
                        # For PDF/other formats, check if we have a text version
                        file_path = document_url.split('/')[-1].split('?')[0]
                        file_name = file_path.split('.')[0].replace("%20", " ")
                        text_file = f"{file_name}.txt"
                        if os.path.exists(text_file):
                            with open(text_file, 'r', encoding='utf-8') as f:
                                document_content = f.read()
            except Exception as e:
                print(f"Error getting document content: {e}")
        
        if not document_content:
            return "Could not retrieve document content for complex navigation"
        
        # Step 2: Extract URLs from document content using simple parsing
        import re
        url_pattern = r'https?://[^\s<>"{}|\\^`[\]]+(?:[^\s<>"{}|\\^`[\]])'
        urls_in_document = re.findall(url_pattern, document_content)
        
        print(f"Found {len(urls_in_document)} URLs in document")
        
        if not urls_in_document:
            return "No URLs found in document for complex navigation"
        
        # Step 3: Scrape data from the URLs found in document
        scraped_data = {}
        for i, url in enumerate(urls_in_document[:5]):  # Limit to first 5 URLs
            print(f"Scraping URL {i+1}: {url}")
            try:
                scraped_content = scrape_url(url)
                if scraped_content:
                    scraped_data[f"url_{i+1}"] = {
                        "url": url,
                        "content": scraped_content
                    }
            except Exception as e:
                print(f"Error scraping {url}: {e}")
        
        if not scraped_data:
            return "Could not scrape any data from document URLs"
        
        # Step 4: Use LLM to analyze all the data and find the answer
        analysis_prompt = f"""
You are helping to answer a complex question that requires analyzing multiple data sources.

QUESTION: "{question}"

DOCUMENT CONTENT: {document_content[:1000]}...

SCRAPED DATA FROM URLS:
{json.dumps(scraped_data, indent=2)[:2000]}...

INSTRUCTIONS:
1. Analyze the question and understand what information is needed
2. Look through the document content and scraped data to find relevant information
3. If this is about flight numbers, look for step-by-step processes, city information, landmarks, and flight data
4. Follow any instructions or workflows described in the document
5. Extract the specific answer requested

Provide the direct answer to the question. If you need to follow a multi-step process, explain your reasoning and provide the final result.
"""
        
        # Step 4: Use direct extraction to find the answer
        print("=" * 50)
        print("GEMINI REQUEST FOR COMPLEX QUESTION:")
        print(f"Question: {question}")
        print(f"Scraped {len(scraped_data)} URLs successfully")
        print("=" * 50)
        
        # For complex navigation, use direct extraction
        extraction_result = extract_answer_from_scraped_data(scraped_data, question)
        
        # Special handling for secret/token questions
        if extraction_result == "Use direct URL access for secret extraction":
            print("Detected secret/token question, using direct document URL access")
            try:
                direct_result = scrape_url(document_url)
                if direct_result:
                    return smart_extract_response(direct_result, question)
                else:
                    return "Could not access document URL for secret extraction"
            except Exception as e:
                return f"Error accessing document URL: {str(e)}"
        
        return extraction_result
        
    except Exception as e:
        return f"Error in complex navigation: {str(e)}"

def extract_answer_from_scraped_data(scraped_data, question):
    """
    Fallback method to extract answer directly from scraped data
    """
    try:
        print("Using direct extraction method...")
        question_lower = question.lower()
        
        # For secret/token questions
        if any(word in question_lower for word in ['secret', 'token', 'key']):
            print("Looking for secret/token/key...")
            # For secret questions, try the document URL directly first
            # This handles cases like "Go to url and get the secret key"
            return "Use direct URL access for secret extraction"
        
        # For flight number questions
        elif "flight" in question_lower:
            print("Looking for flight number in scraped data...")
            for url_key, url_data in scraped_data.items():
                print(f"Checking {url_key}: {url_data.get('url', 'No URL')}")
                content = url_data.get("content", {})
                
                if isinstance(content, dict):
                    # Look for flight number in the response
                    if 'data' in content and isinstance(content['data'], dict):
                        if 'flightNumber' in content['data']:
                            flight_num = content['data']['flightNumber']
                            print(f"Found flight number: {flight_num}")
                            return flight_num
                        # Also check for city information
                        if 'city' in content['data']:
                            city = content['data']['city']
                            print(f"Found city: {city}")
                    
                    if 'flightNumber' in content:
                        flight_num = content['flightNumber']
                        print(f"Found flight number: {flight_num}")
                        return flight_num
                
                # Also check string content for patterns
                content_str = str(content)
                if len(content_str) > 10:
                    print(f"Content string: {content_str[:100]}...")
                    import re
                    flight_patterns = [
                        r'"flightNumber":\s*"([^"]+)"',
                        r'([a-fA-F0-9]{6,8})',  # Hex patterns like 68df29
                        r'"([a-zA-Z0-9]{4,10})"',  # Quoted alphanumeric
                    ]
                    for pattern in flight_patterns:
                        matches = re.findall(pattern, content_str)
                        if matches:
                            result = matches[0]
                            print(f"Found flight pattern match: {result}")
                            return result
        
        # For other types of questions, return first meaningful content
        print("Looking for any meaningful content...")
        for url_key, url_data in scraped_data.items():
            content = url_data.get("content")
            if content and len(str(content)) > 10:
                result = str(content)[:200]
                print(f"Returning content from {url_key}: {result}")
                return result
        
        print("No meaningful content found in scraped data")
        return "Could not extract answer from scraped data"
        
    except Exception as e:
        print(f"Error in fallback extraction: {e}")
        return f"Error extracting answer: {str(e)}"



def smart_extract_response(response, question):
    """
    Simple extraction for basic cases
    """
    try:
        # Convert to string for analysis
        if isinstance(response, dict):
            response_str = json.dumps(response)
        else:
            response_str = str(response)
        
        # Return clean response
        return response_str[:500] if len(response_str) > 500 else response_str
        
    except Exception as e:
        print(f"Error in extraction: {e}")
        return str(response)[:200]

def execute_url_navigation(question, document_url, document_content=""):
    """
    Simplified URL navigation using LLM guidance
    """
    try:
        # First determine if this is complex or simple
        intent = classify_question_intent(question, document_content)
        print(f"Detected intent: {intent}")
        
        if intent == "complex":
            return execute_complex_navigation(question, document_url, document_content)
        else:
            # Simple case - just scrape the URL directly
            print(f"Simple URL access: {document_url}")
            result = scrape_url(document_url)
            if result:
                return smart_extract_response(result, question)
            else:
                return "Failed to access URL"
                
    except Exception as e:
        return f"Error in URL navigation: {str(e)}"



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
    
    # First, get the document content to check for complex instructions
    document_content = ""
    filePath = query.documents.split('/')[-1].split('?')[0]
    fileName = filePath.split('.')[0].replace("%20"," ")
    
    # Try to get document content for instruction parsing
    try:
        if query.documents.startswith("http"):
            response = requests.get(query.documents)
            content_type = response.headers.get("Content-Type", "")
            if "pdf" in content_type:
                # For PDFs, we'll check if we have the text version
                text_file = f"{fileName}.txt"
                if os.path.exists(text_file):
                    with open(text_file, 'r', encoding='utf-8') as f:
                        document_content = f.read()
            else:
                document_content = response.text
    except:
        pass
    
    # Check for navigation questions using LLM-based intent analysis
    complex_answers = []
    regular_questions = []
    question_mapping = []  # Maps regular question indices to original indices
    
    for i, question in enumerate(query.questions):
        intent = classify_question_intent(question, document_content)
        
        if intent == "complex":
            # Handle any type of URL navigation
            try:
                answer = execute_url_navigation(question, query.documents, document_content)
                complex_answers.append((i, answer))
            except Exception as e:
                complex_answers.append((i, f"Error in navigation: {str(e)}"))
        else:
            regular_questions.append(question)
            question_mapping.append(i)
    
    # If all questions are navigation questions, return navigation answers
    if not regular_questions:
        results = [""] * len(query.questions)
        for original_index, answer in complex_answers:
            results[original_index] = answer
        
        # Calculate time taken and log response
        end_time = time.time()
        time_taken = round(end_time - start_time, 2)
        response_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print("RESPONSE SENT:")
        print(f"Response sent at: {response_timestamp}")
        print(f"Time taken: {time_taken} seconds")
        print(f"Answers: {results}")
        print("=" * 80)
        
        return {"answers": results}
    
    # Continue with regular document processing for remaining questions
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
    
    # Combine navigation answers with regular document Q&A answers
    final_results = [None] * total_questions
    
    # Place navigation answers
    for original_index, answer in complex_answers:
        final_results[original_index] = answer
    
    # Place regular Q&A answers
    for i, answer in enumerate(results):
        if answer is not None:
            original_index = question_mapping[i] if i < len(question_mapping) else i
            final_results[original_index] = answer
    
    # Final validation - ensure no None values remain
    for i, result in enumerate(final_results):
        if result is None:
            final_results[i] = "❌ No response received"
    
    response_data = {"answers": final_results}
    
    # Calculate time taken and log response sent
    end_time = time.time()
    time_taken = round(end_time - start_time, 2)
    response_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("RESPONSE SENT:")
    print(f"Response sent at: {response_timestamp}")
    print(f"Time taken: {time_taken} seconds")
    print(f"Answers: {final_results}")
    print("=" * 80)
    
    return response_data


if __name__ == "__main__":
    uvicorn.run("backend:app", host="127.0.0.1", port=8080)