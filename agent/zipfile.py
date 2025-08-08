import zipfile
import os
import shutil

# List of allowed document extensions
DOCUMENT_EXTENSIONS = {'.txt', '.pdf', '.docx', '.pptx', '.xlsx'}

def extract_nested_zip(zip_path, extract_dir):
    """
    Recursively extract zip files, including nested zip files.
    """
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    # Walk through the extracted files
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            file_path = os.path.join(root, file)

            # If a ZIP file is found, extract it recursively
            if zipfile.is_zipfile(file_path):
                nested_dir = os.path.splitext(file_path)[0]
                os.makedirs(nested_dir, exist_ok=True)
                extract_nested_zip(file_path, nested_dir)

def collect_documents(extract_dir, output_dir):
    """
    Copy all files with matching document extensions to output_dir.
    """
    os.makedirs(output_dir, exist_ok=True)
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if os.path.splitext(file)[1].lower() in DOCUMENT_EXTENSIONS:
                src_path = os.path.join(root, file)
                dst_path = os.path.join(output_dir, file)
                shutil.copy2(src_path, dst_path)

def process_zip(zip_file_path, working_dir='extracted_temp', output_dir='documents'):
    """
    Process the outer zip file and collect all documents inside.
    """
    if os.path.exists(working_dir):
        shutil.rmtree(working_dir)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    os.makedirs(working_dir)
    extract_nested_zip(zip_file_path, working_dir)
    collect_documents(working_dir, output_dir)
    print(f"Documents saved to: {output_dir}")

# Example usage
zip_file = 'unknownDoc/hackrx_pdf.zip'
process_zip(zip_file)
