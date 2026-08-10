import hashlib
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"


def extract_text_from_pdf(path: Path) -> list[str]:
    try:
        import pypdf
    except ImportError:
        try:
            import pdfplumber
        except ImportError:
            logger.error("Install pypdf or pdfplumber: pip install pypdf pdfplumber")
            sys.exit(1)
        with pdfplumber.open(path) as pdf:
            return [page.extract_text() or "" for page in pdf.pages]

    reader = pypdf.PdfReader(path)
    return [page.extract_text() or "" for page in reader.pages]


def chunk_page(page_text: str, source: str, page: int, chunk_size: int = 200, overlap: int = 25) -> list[dict]:
    words = page_text.split()
    if not words:
        return []
    chunks = []
    start = 0
    step = chunk_size - overlap
    while start < len(words):
        end = min(start + chunk_size, len(words))
        text = " ".join(words[start:end])
        chunk_id = hashlib.md5(f"{source}:p{page}:{start}".encode()).hexdigest()[:16]
        chunks.append({"id": chunk_id, "text": text, "source": source, "page": page})
        if end == len(words):
            break
        start += step
    return chunks


def chunk_text(text: str, source: str, chunk_size: int = 200, overlap: int = 25) -> list[dict]:
    chunks = []
    for page_idx, page_text in enumerate(text.split("\n\n<<PAGE>>\n\n")):
        chunks.extend(chunk_page(page_text, source, page=page_idx, chunk_size=chunk_size, overlap=overlap))
    return chunks


def ingest_all(embedding_service, data_dir: Path = DATA_DIR, namespace: str = "default"):
    pdf_files = list(data_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning("No PDFs found in %s", data_dir)
        return

    all_chunks = []
    for pdf_path in pdf_files:
        logger.info("Processing %s...", pdf_path.name)
        pages = extract_text_from_pdf(pdf_path)
        page_text = "\n\n<<PAGE>>\n\n".join(pages)
        chunks = chunk_text(page_text, source=pdf_path.name)
        logger.info("  -> %d chunks", len(chunks))
        all_chunks.extend(chunks)

    if not all_chunks:
        logger.warning("No chunks extracted from any PDF")
        return

    logger.info("Indexing %d chunks into Pinecone...", len(all_chunks))
    count = embedding_service.index_chunks(all_chunks, namespace=namespace)
    logger.info("Done — %d vectors upserted", count)


def main():
    from app.embeddings.service import EmbeddingService
    svc = EmbeddingService()
    ingest_all(svc)


if __name__ == "__main__":
    main()
