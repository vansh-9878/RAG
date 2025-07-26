from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from dotenv import load_dotenv
import os

load_dotenv()

def readPDF(file_path:str):
    endpoint = os.getenv('ocr_endpoint')
    key = os.getenv('key1')

    client = DocumentIntelligenceClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(key)
)

    model_id = "prebuilt-read"

    with open(file_path, "rb") as f:
        poller = client.begin_analyze_document(
        model_id=model_id,
        body=f,
        content_type="application/octet-stream"
    )

    result = poller.result()

    with open("extracted2.txt",'w',encoding='utf-8') as f:    
        for page in result.pages:
            for line in page.lines:
                f.write(line.content + "\n")

