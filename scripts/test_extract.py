import csv
import fitz

from app.chunking import chunk_text

with open("data/manifest.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        filepath = f"data/raw/{row['filename']}"
        doc = fitz.open(filepath)

        full_text = ""
        for page in doc:
            full_text += page.get_text()

        char_count = len(full_text)
        preview = full_text[:100].replace("\n", " ")

        status = "OK" if char_count > 200 else "SUSPICIOUSLY SHORT — check this one"
        #print(f"[{status}] {row['filename']} — {char_count} characters — preview: {preview}")
        
path = "data/raw/T1DbreakthroughsNIH.pdf"

doc = fitz.open(path)
full_text = ""
for page in doc:
    full_text += page.get_text()

chunks = chunk_text(full_text)

print(f"Total characters extracted: {len(full_text)}")
print(f"Total chunks: {len(chunks)}")
print()
print("--- End of chunk 1 (last 200 characters) ---")
print(chunks[0][-200:])
print()
print("--- Start of chunk 2 (first 200 characters) ---")
print(chunks[1][:200])