import fitz 

def pdf_to_text(fileName):
    filePath=f"{fileName}.pdf"
    doc = fitz.open(filePath)
    
    all_text = ""
    for page in doc:
        all_text += page.get_text()
    
    doc.close()
    
    with open(f"{fileName}.txt", "w", encoding="utf-8") as f:
        f.write(all_text)

# pdf_to_text("travel_insurance")
