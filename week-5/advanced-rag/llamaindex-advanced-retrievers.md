# Advanced Retrievers in LlamaIndex

## Learning Objectives
- Identify the different index types in LlamaIndex and know when to use each
- Explore core and advanced retrievers that power flexible search strategies
- Understand fusion techniques that combine results from multiple queries
- Match retrievers to the most suitable use cases

---

## 1. Core Index Types

LlamaIndex offers three core index types, each optimized for a different retrieval strategy.

```mermaid
flowchart TD
    A[LlamaIndex Core Index Types] --> B[VectorStoreIndex]
    A --> C[DocumentSummaryIndex]
    A --> D[KeywordTableIndex]

    B --> B1[Semantic search via embeddings]
    C --> C1[Summary-based document filtering]
    D --> D1[Exact keyword matching]
```

### 1.1 VectorStoreIndex
- Stores **vector embeddings** for each document chunk.
- Best suited for **semantic retrieval** (meaning-based, not exact word match).
- Commonly used in LLM-powered pipelines (RAG).

### 1.2 DocumentSummaryIndex
- Generates and stores **summaries of documents** at indexing time.
- Summaries are used to **filter documents** before retrieving full content.
- Especially useful for **large and diverse document sets** that can't fit into an LLM's context window.

### 1.3 KeywordTableIndex
- Extracts **keywords** from documents.
- Maps keywords to specific content chunks.
- Ideal for **exact keyword matching** and **hybrid/rule-based search** scenarios.

---

## 2. Core Retrievers

### 2.1 Vector Index Retriever
- Uses vector embeddings to find **semantically relevant** content.
- Ideal for **general-purpose search** and RAG pipelines.

```mermaid
flowchart LR
    Q[Query] --> E[Embed Query]
    E --> S[Similarity Search over Vector Store]
    S --> R[Top-K Semantically Similar Chunks]
```

### 2.2 TF-IDF (Foundational Concept)
Before BM25, it helps to understand TF-IDF — the foundation of keyword-based search.

| Component | Meaning |
|---|---|
| **TF** (Term Frequency) | How often a word appears in a document |
| **IDF** (Inverse Document Frequency) | How rare that word is across all documents |
| **TF-IDF Score** | TF × IDF — highlights words frequent in one document but rare across the collection |

```mermaid
flowchart LR
    TF[Term Frequency<br/>how often in doc] --> M[TF-IDF Score]
    IDF[Inverse Document Frequency<br/>how rare across corpus] --> M
    M --> O[Highlights distinctive, high-signal terms]
```

### 2.3 BM25 Retriever
- A **keyword-based** ranking method, built on TF-IDF foundations.
- Retrieves based on **exact keyword match**, not semantic similarity.
- Improvements over TF-IDF:
  - **Term frequency saturation** — reduces the impact of repeated terms.
  - **Document length normalization** — adjusts scoring for longer/shorter documents.

```mermaid
flowchart TD
    TFIDF[TF-IDF] -->|adds term frequency saturation| BM25[BM25 Retriever]
    TFIDF -->|adds document length normalization| BM25
    BM25 --> O[More robust keyword ranking]
```

---

## 3. Advanced Retrievers

### 3.1 Document Summary Index Retriever
- Uses **document summaries** (not full documents) to find relevant content.
- Two variants:

```mermaid
flowchart TD
    Q[Query] --> DSIR[Document Summary Index Retriever]
    DSIR --> V1["LLM-based\n(uses LLM to judge relevance)"]
    DSIR --> V2["Embedding-based\n(semantic similarity: query vs summary embedding)"]
    V1 --> Cost[More accurate but slower/costlier]
    V2 --> Eff[More efficient for large collections]
    V1 --> Ret[Returns ORIGINAL documents, not summaries]
    V2 --> Ret
```

> Regardless of variant used, this retriever always **returns the original documents**, not their summaries — summaries are only used to select which docs to retrieve.

### 3.2 Auto Merging Retriever
- Preserves context in **long documents** using a **hierarchical structure**.
- Uses hierarchical chunking to create **parent** and **child** nodes.
- If enough child nodes from the same parent are retrieved, the retriever **merges up** and returns the parent node instead — consolidating related content and preserving broader context.

```mermaid
flowchart TD
    P[Parent Node] --> C1[Child Node 1]
    P --> C2[Child Node 2]
    P --> C3[Child Node 3]

    C1 -.retrieved.-> Check{Enough children<br/>from same parent<br/>retrieved?}
    C2 -.retrieved.-> Check
    Check -->|Yes| Merge[Return Parent Node]
    Check -->|No| Individual[Return individual Child Nodes]
```

### 3.3 Recursive Retriever
- Follows **relationships between nodes** using references.
- Can follow references such as **citations** (academic papers) or **metadata links**.
- Supports both:
  - **Chunk references** (node-to-node within/across documents)
  - **Metadata references**
- Enables retrieval of related content across documents or layers of abstraction.

```mermaid
flowchart LR
    N1[Node A<br/>Main Document] -- reference/citation --> N2[Node B<br/>Cited Document]
    N1 -- metadata link --> N3[Node C<br/>Related Metadata]
    N2 -- reference --> N4[Node D<br/>Further Citation]
```

### 3.4 Query Fusion Retriever
- Combines results from **different retrievers** (e.g., vector-based + keyword-based).
- Optionally generates **multiple query variations** via an LLM to improve coverage.
- Merges results using a **fusion strategy** to improve recall.

```mermaid
flowchart TD
    Q[Original Query] --> QG[Optional: LLM generates<br/>query variations]
    QG --> Q1[Query Variant 1]
    QG --> Q2[Query Variant 2]
    Q --> VR[Vector Index Retriever]
    Q --> BM[BM25 Retriever]
    Q1 --> VR
    Q2 --> BM

    VR --> Results1[Result Set 1]
    BM --> Results2[Result Set 2]

    Results1 --> Fusion[Fusion Strategy]
    Results2 --> Fusion
    Fusion --> Final[Merged / Re-ranked Results]
```

---

## 4. Fusion Strategies

```mermaid
flowchart TD
    F[Query Fusion Retriever<br/>Fusion Strategies] --> RRF[Reciprocal Rank Fusion]
    F --> RSF[Relative Score Fusion]
    F --> DBF[Distribution-Based Fusion]

    RRF --> RRF1["Scores by rank position\n(higher score for top-ranked docs)\nRobust, ignores score magnitude"]
    RSF --> RSF1["Normalizes scores by dividing by max score\nPreserves relative confidence per retriever"]
    DBF --> DBF1["Statistical normalization\n(z-score, percentile ranking)\nHandles score variability well"]
```

| Strategy | How it works | Best for |
|---|---|---|
| **Reciprocal Rank Fusion (RRF)** | Assigns higher scores to documents ranked near the top of any list | Robust fusion without relying on score magnitudes |
| **Relative Score Fusion** | Normalizes scores within each result set by dividing by the max score | Preserving each retriever's relative confidence |
| **Distribution-Based Fusion** | Uses z-score normalization / percentile ranking | Handling score variability across retrievers |

---

## 5. Use Case Recommendations

```mermaid
flowchart TD
    UC[Use Case] --> QA[General Q&A]
    UC --> Tech[Technical Documents]
    UC --> Long[Long Documents]
    UC --> Research[Research Papers]
    UC --> Large[Large Document Sets]

    QA --> QA1["Vector Index Retriever\n+ BM25 (fusion)\nsemantic + keyword matching"]
    Tech --> Tech1["BM25 as primary\n+ Vector Index Retriever as secondary\nexact terms prioritized, semantic flexibility added"]
    Long --> Long1["Auto Merging Retriever\nmerges child → parent for broader context"]
    Research --> Research1["Recursive Retriever\nfollows citations to related papers"]
    Large --> Large1["Document Summary Index Retriever\n→ narrows candidate docs\n→ then Vector Search within subset"]
```

| Use Case | Recommended Retriever(s) | Why |
|---|---|---|
| General Q&A | Vector Index Retriever + BM25 | Combines semantic relevance with keyword matching |
| Technical documents (exact terms matter) | BM25 (primary) + Vector Index Retriever (secondary) | Prioritizes exact terms, adds contextual flexibility |
| Long documents | Auto Merging Retriever | Returns parent context only when enough child evidence is found |
| Research papers | Recursive Retriever | Follows citations to retrieve relevant cited content |
| Large document sets | Document Summary Index Retriever → Vector Search | Narrows candidates via summaries, then does precise search within the subset |

---

## 6. Summary Cheat Sheet

```mermaid
mindmap
  root((LlamaIndex<br/>Advanced Retrieval))
    Index Types
      VectorStoreIndex
        semantic embeddings
      DocumentSummaryIndex
        summary-based filtering
      KeywordTableIndex
        keyword → chunk mapping
    Core Retrievers
      Vector Index Retriever
        semantic, general-purpose
      BM25 Retriever
        keyword, TF saturation, length norm
    Advanced Retrievers
      Document Summary Index Retriever
        LLM-based or embedding-based
        returns original docs
      Auto Merging Retriever
        parent/child hierarchy
        long documents
      Recursive Retriever
        citations & metadata links
        research papers
      Query Fusion Retriever
        combines multiple retrievers
        optional LLM query expansion
    Fusion Strategies
      Reciprocal Rank Fusion
      Relative Score Fusion
      Distribution-Based Fusion
```

### Key Takeaways
1. **Three core indexes**: VectorStoreIndex (semantic), DocumentSummaryIndex (summary filtering), KeywordTableIndex (keyword mapping).
2. **Vector Index Retriever** = general-purpose semantic search, backbone of RAG.
3. **BM25** improves on TF-IDF via term frequency saturation + document length normalization.
4. **Document Summary Index Retriever** filters using summaries but always returns full original documents.
5. **Auto Merging Retriever** preserves context in long docs by merging child nodes into parent nodes.
6. **Recursive Retriever** follows citation/metadata references across documents.
7. **Query Fusion Retriever** combines multiple retrievers (and optionally LLM-generated query variants), merged via RRF, Relative Score, or Distribution-Based fusion.
8. Retriever choice should be driven by **document structure and query type** — general Q&A, technical precision, long-form context, citation-heavy research, or massive corpora each favor a different retriever (or combination).
