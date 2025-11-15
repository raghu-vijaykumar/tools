"""
Knowledge base indexer for the writer tool.
Handles loading, chunking, embedding, and storing documents in a vector database.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from common.embeddings import get_embeddings


class KnowledgeIndexer:
    """Indexes a folder of documents for retrieval."""

    def __init__(
        self,
        folder_path: str,
        embedding_provider: str = "openai",
        embedding_model: Optional[str] = None,
    ):
        self.folder_path = Path(folder_path)
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.embeddings = self._get_embeddings()
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.folder_path / ".chroma")
        )
        self.collection = self.chroma_client.get_or_create_collection("knowledge_base")

    def _get_embeddings(self):
        """Get embeddings model."""
        return get_embeddings(
            provider=self.embedding_provider, model=self.embedding_model
        )

    def _extract_text_from_file(self, file_path: Path) -> str:
        """Extract text from various file types."""
        if file_path.suffix.lower() == ".pdf":
            with open(file_path, "rb") as f:
                pdf = PdfReader(f)
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
                return text
        else:  # txt, md, py, java, json, yaml, etc.
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    def _should_index_file(self, file_path: Path) -> bool:
        """Check if file should be indexed (skip hidden, tmp, etc.)."""
        # Skip hidden files and directories
        if file_path.name.startswith("."):
            return False

        # Skip common non-content files
        skip_extensions = {
            ".pyc",
            ".pyo",
            ".pyd",
            ".class",
            ".jar",
            ".zip",
            ".tar",
            ".gz",
        }
        if file_path.suffix.lower() in skip_extensions:
            return False

        # Skip specific files
        skip_files = {"__pycache__", "node_modules", ".git", "env", "venv"}
        if any(part in skip_files for part in file_path.parts):
            return False

        return True

    def _load_folder(self) -> List[Dict]:
        """Load all indexable files from the folder."""
        documents = []

        for file_path in self.folder_path.rglob("*"):
            if file_path.is_file() and self._should_index_file(file_path):
                try:
                    text = self._extract_text_from_file(file_path)
                    if text.strip():  # Only index non-empty files
                        documents.append(
                            {
                                "content": text,
                                "filepath": str(
                                    file_path.relative_to(self.folder_path)
                                ),
                                "last_modified": datetime.fromtimestamp(
                                    file_path.stat().st_mtime
                                ).isoformat(),
                            }
                        )
                except Exception as e:
                    print(f"Warning: Could not process {file_path}: {e}")

        return documents

    def _chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        """Chunk documents into smaller pieces."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,  # ~800 tokens
            chunk_overlap=150,  # ~150 tokens overlap
            separators=["\n\n", "\n", " ", ""],
        )

        chunked_docs = []
        for doc in documents:
            chunks = text_splitter.split_text(doc["content"])
            for i, chunk in enumerate(chunks):
                chunked_docs.append(
                    {
                        "content": chunk,
                        "filepath": doc["filepath"],
                        "last_modified": doc["last_modified"],
                        "chunk_id": i,
                    }
                )

        return chunked_docs

    def index_documents(self) -> None:
        """Index all documents in the folder."""
        print(f"Indexing knowledge base at {self.folder_path}...")

        # Load and chunk documents
        documents = self._load_folder()
        chunked_docs = self._chunk_documents(documents)

        print(f"Found {len(documents)} files, created {len(chunked_docs)} chunks")

        if not chunked_docs:
            print("No documents to index!")
            return

        # Clear existing index if re-indexing
        try:
            self.chroma_client.delete_collection("knowledge_base")
            self.collection = self.chroma_client.create_collection("knowledge_base")
        except:
            pass

        # Embed and store
        texts = [doc["content"] for doc in chunked_docs]
        embeddings = self.embeddings.embed_documents(texts)

        # Prepare metadata
        metadatas = []
        ids = []
        for i, doc in enumerate(chunked_docs):
            metadatas.append(
                {
                    "filepath": doc["filepath"],
                    "last_modified": doc["last_modified"],
                    "chunk_id": str(doc["chunk_id"]),
                }
            )
            ids.append(f"{doc['filepath']}_chunk_{doc['chunk_id']}")

        # Add to vector store
        self.collection.add(
            embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids
        )

        print(f"Indexed {len(chunked_docs)} chunks successfully")


class KnowledgeRetriever:
    """Retrieves relevant documents from the indexed knowledge base."""

    def __init__(
        self,
        folder_path: str,
        embedding_provider: str = "openai",
        embedding_model: Optional[str] = None,
    ):
        self.folder_path = Path(folder_path)
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.folder_path / ".chroma")
        )
        self.collection = self.chroma_client.get_collection("knowledge_base")
        self.embeddings = get_embeddings(
            provider=embedding_provider, model=embedding_model
        )

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant documents for a query."""
        query_embedding = self.embeddings.embed_query(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        retrieved_docs = []
        for i in range(len(results["documents"][0])):
            retrieved_docs.append(
                {
                    "content": results["documents"][0][i],
                    "filepath": results["metadatas"][0][i]["filepath"],
                    "chunk_id": int(results["metadatas"][0][i]["chunk_id"]),
                    "distance": results["distances"][0][i],
                }
            )

        return retrieved_docs

    def is_indexed(self) -> bool:
        """Check if the knowledge base has been indexed."""
        try:
            count = self.collection.count()
            return count > 0
        except:
            return False
