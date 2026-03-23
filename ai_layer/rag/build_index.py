import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
INDEX_DIR = BASE_DIR / "index"

EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def load_pdfs():
    pdfs = sorted([p for p in DOCS_DIR.rglob("*.pdf")])
    if not pdfs:
        raise SystemExit(f"No PDFs found. Put text PDFs into: {DOCS_DIR}")

    docs = []
    for pdf in pdfs:
        print(f"📘 Loading: {pdf.name}") 
        loader = PyPDFLoader(str(pdf))
        loaded = loader.load()
        # Add filename metadata for citation
        for d in loaded:
            d.metadata["source_file"] = pdf.name
            d.metadata["page"] = d.metadata.get("page", None)
        docs.extend(loaded)

    return docs


def main():
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    print(f"📄 Loading PDFs from: {DOCS_DIR}")
    documents = load_pdfs()

    splitter = RecursiveCharacterTextSplitter(chunk_size=8000, chunk_overlap=400)
    chunks = splitter.split_documents(documents)

    print(f"✂️  Split into {len(chunks)} chunks")

    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME)

    print(f"🧠 Creating embeddings locally using: {EMBED_MODEL_NAME}")
    db = FAISS.from_documents(chunks, embeddings)

    db.save_local(str(INDEX_DIR))
    print(f"✅ FAISS index saved to: {INDEX_DIR}")


if __name__ == "__main__":
    main()
