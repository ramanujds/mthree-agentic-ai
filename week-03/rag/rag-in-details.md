# RAG in Detail — the Retrieval, Embedding & Generation Pipeline

Notes on how RAG actually works under the hood (embeddings, chunking, distance
metrics, top-K retrieval). Companion to [what-is-rag.md](what-is-rag.md).

## Why domain-specific knowledge needs RAG

Pre-trained LLMs are strong at general tasks but weak on **specialized /
private knowledge** they were never trained on — e.g. a company's internal
mobile device policy. That data is confidential and not on the public
internet, so the base model simply doesn't know it.

RAG fixes this **without retraining the model**: it plugs an external
knowledge base (trained chatbot data, internal policies, large documents,
etc.) into the generation process at query time.

## The two components of RAG

- **Retriever** — the core of RAG. Finds the knowledge-base content relevant
  to the user's prompt.
- **Generator** — functions as the chatbot. Takes the retrieved content plus
  the original prompt and produces the natural-language answer.

## The four-step RAG pipeline

```mermaid
flowchart LR
    S1["1. Text Embedding<br/>prompt + KB docs → vectors"] --> S2["2. Retrieval<br/>match similar vectors"]
    S2 --> S3["3. Augmented Query Creation<br/>retrieved text + original prompt"]
    S3 --> S4["4. Model Generation<br/>LLM answers using augmented query"]
```

1. **Text embedding** — the prompt is converted into a high-dimensional
   vector via a *question encoder*; knowledge-base documents are separately
   converted into vectors via a *context encoder* (the two encoders can also
   be the same model — simpler, but usually less effective).
2. **Retrieval** — the system compares the prompt's vector against the
   knowledge base's vectors and finds the closest matches.
3. **Augmented query creation** — the text behind the retrieved vectors is
   combined with the original prompt into one augmented query.
4. **Model generation** — the LLM generates the final response from that
   augmented query, grounded in the retrieved knowledge-base content.

## Step 1a: Encoding the prompt

The prompt is encoded using **token embedding + vector averaging**:

```mermaid
flowchart LR
    P["Prompt"] --> T["Tokenize<br/>(words / sub-words)"]
    T --> E["Embed each token<br/>via pre-trained model<br/>(e.g. BERT, GPT)"]
    E --> AVG["Average all<br/>token vectors"]
    AVG --> V["Single prompt vector"]
```

Each token gets embedded into a high-dimensional vector using a pre-trained
token-embedding model (e.g. **BERT**, **GPT**). Averaging all token vectors
produces one vector that concisely captures the meaning of the whole prompt.

## Step 1b: Encoding the knowledge base

Large source documents (e.g. the company's mobile policy) are too big to feed
directly to a chatbot, so they go through a **chunk → embed → index**
pipeline:

```mermaid
flowchart TD
    D["Large source document<br/>(e.g. mobile policy)"] --> C["Chunk into smaller,<br/>manageable text pieces"]
    C --> E2["Embed each chunk<br/>(token embedding + averaging)"]
    E2 --> IDX["Index into vector DB<br/>keyed by chunk ID"]
```

- The document is broken into smaller chunks for targeted, efficient
  retrieval.
- Each chunk is tokenized, each token embedded, then averaged into a single
  chunk-level vector — the same technique used for the prompt.
- Chunk vectors are stored in a **vector database**, keyed by **chunk ID**,
  which is what distance operations use to look up matches later.

## Step 2: Retrieval via distance metrics

To find relevant chunks, the system compares the **prompt vector `q`**
against every **context/chunk vector** (`c1`, `c2`, ...) using a distance
metric.

```mermaid
flowchart LR
    Q["Prompt vector q"] --> CMP{"Compare against<br/>every chunk vector<br/>c1, c2, ..."}
    CMP --> DP["Dot product<br/>(direction + magnitude)"]
    CMP --> COS["Cosine similarity<br/>(direction only)"]
    DP --> RANK["Rank chunks by score"]
    COS --> RANK
    RANK --> TOPK["Select top-K closest chunks<br/>(K = hyperparameter)"]
```

Two common metrics, and they can disagree:

| Metric | What it measures | Notes from the example |
| --- | --- | --- |
| **Dot product** | Both direction *and* magnitude — rewards overall alignment | Found `c2` slightly closer than `c1` |
| **Cosine similarity** | Only the angular direction | Also favored `c2` |

Rule of thumb: dot product is preferable when vector **magnitude** matters;
cosine distance is preferable when only **direction** matters.

### Top-K selection

- `K` is a hyperparameter — the video's example selects **3–5** context
  chunks to bring in as relevant grounding.
- Worked example: out of 7 chunks in the mobile policy, chunk IDs **6, 2, 0**
  are chosen as the top-K most relevant to the query.
- In production, this search runs over a large chunk library, so vector
  databases use approximate-nearest-neighbor indexing to keep it fast.

## Step 3 & 4: Augment and generate

```mermaid
sequenceDiagram
    actor User
    participant Encoder as Question Encoder
    participant VDB as Vector DB (Knowledge Base)
    participant Gen as Generator (Chatbot/LLM)

    User->>Encoder: Prompt ("What is the mobile policy?")
    Encoder->>Encoder: Tokenize + embed + average -> prompt vector q
    Encoder->>VDB: Compare q against chunk vectors (dot product / cosine)
    VDB-->>Encoder: Top-K chunks (e.g. chunk IDs 6, 2, 0)
    Encoder->>Gen: Augmented query = retrieved chunk text + original prompt
    Gen-->>User: Generated, policy-grounded response
```

The selected chunk text and the original query are inserted together into
the chatbot, which generates a response grounded in the company's actual
policy content — something the pre-trained model alone could never produce,
since that data was never part of its training set.

## TL;DR pipeline

```mermaid
flowchart LR
    Prompt --> Embed1["Embed prompt"]
    KB["Knowledge base docs"] --> Chunk["Chunk"] --> Embed2["Embed chunks"] --> Index["Index in vector DB"]
    Embed1 --> Retrieve["Retrieve top-K by<br/>dot product / cosine"]
    Index --> Retrieve
    Retrieve --> Augment["Augmented query =<br/>retrieved text + prompt"]
    Augment --> Generate["LLM generates<br/>grounded response"]
```
