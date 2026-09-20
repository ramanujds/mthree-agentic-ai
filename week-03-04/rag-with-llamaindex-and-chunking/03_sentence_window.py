"""
03 - Sentence-window chunking (SentenceWindowNodeParser)

Each node is a SINGLE sentence -- giving very precise embedding matches
-- but every node's metadata also stores a "window" of the surrounding
sentences. At query time, MetadataReplacementPostProcessor swaps the
matched single sentence back out for its window, so the LLM sees enough
context to actually answer. This is a sentence-granularity form of
parent-child chunking. See ../vector-dbs/chunking.md, section 3 and 7.

Run:
    uv run 03_sentence_window.py
"""

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_sentence_window"


def main():
    configure_models()

    parser = SentenceWindowNodeParser.from_defaults(
        window_size=3,
        window_metadata_key="window",
        original_text_metadata_key="original_sentence",
    )
    document = Document(text=load_handbook_text())
    nodes = parser.get_nodes_from_documents([document])
    print_nodes(nodes, "Sentence-window chunking (1 sentence per node, window=3)")

    # Show that each node's embedded text (1 sentence) differs from the
    # wider window stored in its metadata -- that gap is the whole point.
    sample = nodes[5]
    print("--- Example: embedded sentence vs. stored window ---")
    print(f"Embedded (matched against queries): {sample.get_content()!r}")
    print(f"Window (sent to the LLM instead):   {sample.metadata['window']!r}\n")

    chroma_collection = get_chroma_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    if chroma_collection.count() == 0:
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex(nodes, storage_context=storage_context)
    else:
        index = VectorStoreIndex.from_vector_store(vector_store)

    # The postprocessor is what replaces the matched sentence with its window.
    query_engine = index.as_query_engine(
        similarity_top_k=2,
        node_postprocessors=[MetadataReplacementPostProcessor(target_metadata_key="window")],
    )

    questions = [
        "What is the maximum client meal reimbursement per person, and what's the rule about alcohol?",
        "How many vacation days do employees accrue per year, and how many can be carried over?",
    ]
    for question in questions:
        response = query_engine.query(question)
        print_answer(question, response, response.source_nodes)


if __name__ == "__main__":
    main()
