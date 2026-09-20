"""
01 - Fixed-size chunking (TokenTextSplitter)

Splits the document into fixed-size token windows with overlap, with no
regard for sentence or paragraph boundaries. Fast and simple, but chunks
can cut mid-sentence or straddle two unrelated topics -- see
../vector-dbs/chunking.md, section 1 ("Fixed-Size Chunking").

Run:
    uv run 01_fixed_size_chunking.py
"""

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_fixed_size"


def main():
    configure_models()

    splitter = TokenTextSplitter(chunk_size=120, chunk_overlap=20)
    document = Document(text=load_handbook_text())
    nodes = splitter.get_nodes_from_documents([document])
    print_nodes(nodes, "Fixed-size chunking (TokenTextSplitter, chunk_size=120 tokens)")

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
