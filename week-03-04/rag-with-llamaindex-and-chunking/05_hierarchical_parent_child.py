"""
05 - Hierarchical / parent-child chunking (HierarchicalNodeParser + AutoMergingRetriever)

Splits the document into three chunk sizes (large -> medium -> small),
keeping parent/child relationships between them. Only the SMALL "leaf"
nodes are embedded and searched; when enough leaf nodes under the same
parent match a query, AutoMergingRetriever automatically returns the
larger parent chunk instead -- giving the LLM richer context without
losing retrieval precision. See ../vector-dbs/chunking.md, section 7.

Because the parent/child relationships live in a docstore (not in
Chroma, which only stores vectors), this script persists that docstore
to disk itself -- illustrating chunking.md's pitfall that hierarchical
chunking "doubles the indexing complexity": you need to track the
child-to-parent map yourself, not just the vectors.

Run:
    uv run 05_hierarchical_parent_child.py
"""

import os

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.vector_stores.chroma import ChromaVectorStore

from common import (
    configure_models,
    get_chroma_collection,
    load_handbook_text,
    print_answer,
    print_nodes,
)

COLLECTION_NAME = "chunking_hierarchical"
DOCSTORE_PERSIST_DIR = os.path.join(os.path.dirname(__file__), ".docstore_hierarchical")


def main():
    configure_models()

    parser = HierarchicalNodeParser.from_defaults(chunk_sizes=[1024, 256, 64])
    document = Document(text=load_handbook_text())
    all_nodes = parser.get_nodes_from_documents([document])
    leaf_nodes = get_leaf_nodes(all_nodes)
    print_nodes(all_nodes, "All nodes across 3 levels (1024/256/64 tokens)")
    print_nodes(leaf_nodes, "Leaf nodes only (these get embedded + searched)")

    chroma_collection = get_chroma_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    if chroma_collection.count() == 0:
        # Fresh collection: build a docstore with ALL nodes (leaves +
        # parents) so the retriever can resolve a leaf match up to its
        # parent, then persist it -- the docstore is what makes
        # parent-child retrieval possible, and it lives outside Chroma.
        docstore = SimpleDocumentStore()
        docstore.add_documents(all_nodes)
        storage_context = StorageContext.from_defaults(docstore=docstore, vector_store=vector_store)
        index = VectorStoreIndex(leaf_nodes, storage_context=storage_context)
        storage_context.persist(persist_dir=DOCSTORE_PERSIST_DIR)
    else:
        # Reuse the persisted vectors AND the persisted docstore -- without
        # the docstore, auto-merging has no parent/child map to work with.
        docstore = SimpleDocumentStore.from_persist_dir(DOCSTORE_PERSIST_DIR)
        storage_context = StorageContext.from_defaults(docstore=docstore, vector_store=vector_store)
        index = VectorStoreIndex(nodes=[], storage_context=storage_context)

    base_retriever = index.as_retriever(similarity_top_k=6)
    merging_retriever = AutoMergingRetriever(base_retriever, index.storage_context, verbose=True)
    query_engine = RetrieverQueryEngine.from_args(merging_retriever)

    questions = [
        "What is the maximum client meal reimbursement per person, and what's the rule about alcohol?",
        "How many vacation days do employees accrue per year, and how many can be carried over?",
    ]
    for question in questions:
        response = query_engine.query(question)
        print_answer(question, response, response.source_nodes)


if __name__ == "__main__":
    main()
