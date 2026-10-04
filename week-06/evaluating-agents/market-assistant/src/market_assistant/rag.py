"""Knowledge base: markdown docs split by heading, embedded with Ollama into an in-memory vector store."""

from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings

from market_assistant import config


def load_chunks(directory: Path = config.KNOWLEDGE_DIR) -> list[Document]:
    """One chunk per `## ` section, prefixed with the doc title so each chunk is self-describing."""
    chunks: list[Document] = []
    for path in sorted(directory.glob("*.md")):
        head, *sections = path.read_text().split("\n## ")
        title = head.strip().removeprefix("# ").strip()
        for section in sections:
            heading, _, body = section.partition("\n")
            chunks.append(
                Document(
                    page_content=f"{title} - {heading.strip()}\n{body.strip()}",
                    metadata={"source": path.name, "section": heading.strip()},
                )
            )
    return chunks


class Knowledge:
    def __init__(self, directory: Path = config.KNOWLEDGE_DIR):
        embeddings = OllamaEmbeddings(model=config.EMBED_MODEL, base_url=config.OLLAMA_BASE_URL)
        self.store = InMemoryVectorStore(embeddings)
        self.store.add_documents(load_chunks(directory))

    def search(self, query: str, k: int = config.RETRIEVAL_K) -> list[Document]:
        return self.store.similarity_search(query, k=k)
