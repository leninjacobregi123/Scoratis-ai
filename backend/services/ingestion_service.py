"""
Ingestion Service for RAG System
Handles document parsing, chunking, and embedding generation

Enhanced with:
- Async file I/O using aiofiles
- Parallel batch embedding
"""

import logging
import hashlib
import asyncio
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import settings

# Try to import aiofiles for async file I/O
try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ParsedDocument:
    """Result of parsing a document"""
    content: str
    metadata: Dict[str, Any]
    page_count: Optional[int] = None
    word_count: int = 0


@dataclass
class ChunkData:
    """Data for a single chunk"""
    content: str
    chunk_index: int
    metadata: Dict[str, Any]


class IngestionService:
    """
    Service for ingesting documents into the RAG system.

    Handles:
    - File parsing (PDF, DOCX, TXT, HTML, MD)
    - Text chunking with overlap
    - Summary generation
    - Batch embedding generation
    """

    def __init__(self):
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        self._embedding_service = None

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    @property
    def embedding_service(self):
        """Lazy load embedding service to avoid circular imports"""
        if self._embedding_service is None:
            from services.embedding_service import get_embedding_service
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    def parse_file(self, file_path: str, file_type: str) -> ParsedDocument:
        """
        Parse a file and extract its content.

        Args:
            file_path: Path to the file
            file_type: File extension (pdf, docx, txt, html, md)

        Returns:
            ParsedDocument with content and metadata
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_type = file_type.lower().strip(".")

        try:
            if file_type == "pdf":
                return self._parse_pdf(file_path)
            elif file_type == "docx":
                return self._parse_docx(file_path)
            elif file_type in ["txt", "md"]:
                return self._parse_text(file_path)
            elif file_type == "html":
                return self._parse_html(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            raise

    def _parse_pdf(self, file_path: Path) -> ParsedDocument:
        """Parse PDF file using unstructured"""
        try:
            from unstructured.partition.pdf import partition_pdf

            elements = partition_pdf(str(file_path))
            content = "\n\n".join([str(el) for el in elements])
            page_count = len(set(getattr(el.metadata, 'page_number', 1) for el in elements))

            return ParsedDocument(
                content=content,
                metadata={
                    "file_type": "pdf",
                    "file_name": file_path.name,
                    "file_size": file_path.stat().st_size,
                },
                page_count=page_count,
                word_count=len(content.split()),
            )
        except ImportError:
            logger.warning("unstructured not available, falling back to basic PDF parsing")
            return self._parse_pdf_fallback(file_path)

    def _parse_pdf_fallback(self, file_path: Path) -> ParsedDocument:
        """Fallback PDF parsing without unstructured"""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(file_path))
            content_parts = []
            for page in doc:
                content_parts.append(page.get_text())
            content = "\n\n".join(content_parts)

            return ParsedDocument(
                content=content,
                metadata={
                    "file_type": "pdf",
                    "file_name": file_path.name,
                    "file_size": file_path.stat().st_size,
                },
                page_count=len(doc),
                word_count=len(content.split()),
            )
        except ImportError:
            raise ImportError("PDF parsing requires either 'unstructured' or 'PyMuPDF' package")

    def _parse_docx(self, file_path: Path) -> ParsedDocument:
        """Parse DOCX file using unstructured"""
        try:
            from unstructured.partition.docx import partition_docx

            elements = partition_docx(str(file_path))
            content = "\n\n".join([str(el) for el in elements])

            return ParsedDocument(
                content=content,
                metadata={
                    "file_type": "docx",
                    "file_name": file_path.name,
                    "file_size": file_path.stat().st_size,
                },
                word_count=len(content.split()),
            )
        except ImportError:
            logger.warning("unstructured not available, falling back to basic DOCX parsing")
            return self._parse_docx_fallback(file_path)

    def _parse_docx_fallback(self, file_path: Path) -> ParsedDocument:
        """Fallback DOCX parsing without unstructured"""
        try:
            from docx import Document

            doc = Document(str(file_path))
            content_parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    content_parts.append(para.text)
            content = "\n\n".join(content_parts)

            return ParsedDocument(
                content=content,
                metadata={
                    "file_type": "docx",
                    "file_name": file_path.name,
                    "file_size": file_path.stat().st_size,
                },
                word_count=len(content.split()),
            )
        except ImportError:
            raise ImportError("DOCX parsing requires either 'unstructured' or 'python-docx' package")

    def _parse_text(self, file_path: Path) -> ParsedDocument:
        """Parse plain text or markdown file"""
        content = file_path.read_text(encoding="utf-8")

        return ParsedDocument(
            content=content,
            metadata={
                "file_type": file_path.suffix.lstrip("."),
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size,
            },
            word_count=len(content.split()),
        )

    async def _parse_text_async(self, file_path: Path) -> ParsedDocument:
        """Parse plain text or markdown file ASYNCHRONOUSLY"""
        if AIOFILES_AVAILABLE:
            async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                content = await f.read()
        else:
            # Fallback to sync in thread pool
            content = await asyncio.to_thread(file_path.read_text, encoding="utf-8")

        return ParsedDocument(
            content=content,
            metadata={
                "file_type": file_path.suffix.lstrip("."),
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size,
            },
            word_count=len(content.split()),
        )

    async def parse_file_async(self, file_path: str, file_type: str) -> ParsedDocument:
        """
        Parse a file ASYNCHRONOUSLY and extract its content.
        Uses async file I/O for text files, thread pool for others.

        Args:
            file_path: Path to the file
            file_type: File extension (pdf, docx, txt, html, md)

        Returns:
            ParsedDocument with content and metadata
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_type = file_type.lower().strip(".")

        try:
            if file_type in ["txt", "md"]:
                # Use async file reading
                return await self._parse_text_async(file_path)
            else:
                # Use sync parsing in thread pool for complex formats
                return await asyncio.to_thread(self.parse_file, str(file_path), file_type)
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            raise

    def _parse_html(self, file_path: Path) -> ParsedDocument:
        """Parse HTML file"""
        try:
            from unstructured.partition.html import partition_html

            elements = partition_html(str(file_path))
            content = "\n\n".join([str(el) for el in elements])

            return ParsedDocument(
                content=content,
                metadata={
                    "file_type": "html",
                    "file_name": file_path.name,
                    "file_size": file_path.stat().st_size,
                },
                word_count=len(content.split()),
            )
        except ImportError:
            # Fallback to lxml
            from lxml import html as lxml_html

            tree = lxml_html.parse(str(file_path))
            content = tree.getroot().text_content()

            return ParsedDocument(
                content=content,
                metadata={
                    "file_type": "html",
                    "file_name": file_path.name,
                    "file_size": file_path.stat().st_size,
                },
                word_count=len(content.split()),
            )

    def generate_summary(self, content: str, max_length: int = 500) -> str:
        """
        Generate a summary of the document content.

        For now, uses extractive summarization (first N characters).
        Can be enhanced with LLM-based abstractive summarization.

        Args:
            content: Full document content
            max_length: Maximum summary length

        Returns:
            Summary string
        """
        # Clean content
        content = content.strip()

        if len(content) <= max_length:
            return content

        # Simple extractive summary: first sentences up to max_length
        # Find the last sentence boundary before max_length
        truncated = content[:max_length]

        # Try to end at a sentence boundary
        for delimiter in [". ", ".\n", "! ", "? "]:
            last_idx = truncated.rfind(delimiter)
            if last_idx > max_length * 0.5:  # At least half the length
                return truncated[:last_idx + 1].strip()

        # Fall back to word boundary
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.5:
            return truncated[:last_space].strip() + "..."

        return truncated.strip() + "..."

    def chunk_document(
        self,
        content: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> List[ChunkData]:
        """
        Split document content into chunks with metadata.

        Args:
            content: Full document content
            document_metadata: Optional metadata to include in each chunk

        Returns:
            List of ChunkData objects
        """
        if not content or not content.strip():
            return []

        # Use LangChain's text splitter
        texts = self.text_splitter.split_text(content)

        chunks = []
        current_pos = 0

        for i, text in enumerate(texts):
            # Calculate character positions
            start_char = content.find(text, current_pos)
            if start_char == -1:
                start_char = current_pos
            end_char = start_char + len(text)
            current_pos = start_char + 1  # Allow for overlap

            chunk_metadata = {
                "start_char": start_char,
                "end_char": end_char,
                "chunk_size": len(text),
            }

            # Add document metadata if provided
            if document_metadata:
                # Calculate approximate page number for PDFs
                if document_metadata.get("page_count"):
                    total_chars = len(content)
                    page_count = document_metadata["page_count"]
                    approx_page = int((start_char / total_chars) * page_count) + 1
                    chunk_metadata["page_number"] = min(approx_page, page_count)

            chunks.append(ChunkData(
                content=text,
                chunk_index=i,
                metadata=chunk_metadata,
            ))

        logger.info(f"Split document into {len(chunks)} chunks")
        return chunks

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts (sync wrapper).
        For async usage, prefer batch_embed_async.

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Use the sync method from embedding service
        return self.embedding_service.embed_texts(texts)

    async def batch_embed_async(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts ASYNCHRONOUSLY with parallel processing.

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Use async parallel embedding
        return await self.embedding_service.embed_texts_async(texts)

    def compute_content_hash(self, content: str) -> str:
        """
        Compute a hash of the content for deduplication.

        Args:
            content: Document content

        Returns:
            SHA256 hash of content
        """
        return hashlib.sha256(content.encode()).hexdigest()

    def process_text_content(
        self,
        content: str,
        title: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[float], List[ChunkData], List[List[float]]]:
        """
        Process raw text content for ingestion.

        Used for migrating existing journals/conversations.

        Args:
            content: Text content
            title: Document title
            metadata: Optional metadata

        Returns:
            Tuple of (summary, summary_embedding, chunks, chunk_embeddings)
        """
        # Generate summary
        summary = self.generate_summary(content)

        # Generate summary embedding
        summary_embedding = self.embedding_service.embed_text(summary)

        # Chunk the content
        chunks = self.chunk_document(content, metadata)

        # Generate chunk embeddings
        chunk_texts = [chunk.content for chunk in chunks]
        chunk_embeddings = self.batch_embed(chunk_texts)

        return summary, summary_embedding, chunks, chunk_embeddings


# Singleton instance
_ingestion_service: Optional[IngestionService] = None


def get_ingestion_service() -> IngestionService:
    """Get or create the ingestion service singleton"""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = IngestionService()
    return _ingestion_service
