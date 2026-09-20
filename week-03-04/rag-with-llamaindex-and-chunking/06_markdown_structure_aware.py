"""
06 - Structure-aware chunking (MarkdownNodeParser)

Splits along the document's own Markdown headers instead of a raw
character/token count, so each chunk lines up with a real section
("Remote Work Policy", "Vacation Policy", ...) and carries its header
path as metadata. Compare the chunk count/boundaries here against
01/02's token-count-driven splits. Only works well because our sample
document has clean, consistent Markdown headers -- see the pitfalls in
../vector-dbs/chunking.md, section 5.

Run:
    uv run 06_markdown_structure_aware.py
"""

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_markdown_structure"


def main():
    configure_models()

    parser = MarkdownNodeParser()
    document = Document(text=load_handbook_text())
    nodes = parser.get_nodes_from_documents([document])
    print_nodes(nodes, "Structure-aware chunking (MarkdownNodeParser, one chunk per section)")

    # Each node carries its header path as metadata -- print it for the
    # first few nodes to show what structure-aware chunking gives you
    # for free that a size-based splitter doesn't.
    print("--- Header metadata per chunk ---")
    for i, node in enumerate(nodes):
        headers = {k: v for k, v in node.metadata.items() if k.startswith("header")}
        print(f"[{i}] {headers}")
    print()

    chroma_collection = get_chroma_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    if chroma_collection.count() == 0:
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex(nodes, storage_context=storage_context)
    else:
        index = VectorStoreIndex.from_vector_store(vector_store)

    query_engine = index.as_query_engine(similarity_top_k=2)

    questions = [
        "What is the maximum client meal reimbursement per person, and what's the rule about alcohol?",
        "How many vacation days do employees accrue per year, and how many can be carried over?",
    ]
    for question in questions:
        response = query_engine.query(question)
        print_answer(question, response, response.source_nodes)


if __name__ == "__main__":
    main()
