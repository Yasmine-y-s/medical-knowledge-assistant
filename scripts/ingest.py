import csv
import os

import fitz

from app.embeddings import embed

from app.database import SessionLocal
from app.models import DocumentDB, UserDB, Chunk
from app.chunking import chunk_text


UPLOADER_EMAIL = "string@string.com"  # change this to your real registered user


def main():
    db = SessionLocal()

    uploader = db.query(UserDB).filter(UserDB.email == UPLOADER_EMAIL).first()
    if uploader is None:
        raise RuntimeError(f"No user found with email {UPLOADER_EMAIL} — register one first via /register")

    with open("data/manifest.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing = db.query(DocumentDB).filter(DocumentDB.filename == row["filename"]).first()
            if existing is not None:
                print(f"[SKIP] {row['filename']} — already ingested")
                continue

            print(f"[PROCESSING] {row['filename']}")

            document = DocumentDB(
                title=row["title"],
                condition=row["condition"],
                source=row["source"],
                source_url=row["source_url"],
                filename=row["filename"],
                user_id=uploader.id,
            )
            db.add(document)
            db.commit()
            db.refresh(document)

            pdf = fitz.open(f"data/raw/{row['filename']}")
            full_text = ""
            for page in pdf:
                full_text += page.get_text()

            chunks = chunk_text(full_text)

            for index, chunk_content in enumerate(chunks):
                vector = embed(chunk_content)
                chunk_row = Chunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk_content,
                    embedding=vector,
                )
                db.add(chunk_row)

            db.commit()
            print(f"[DONE] {row['filename']} — {len(chunks)} chunks")

    db.close()


if __name__ == "__main__":
    main()