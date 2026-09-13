# Vector Databases — Introduction

## 1. Why Vector Databases?

Traditional (relational) databases store data in **tables** — great for structured,
tabular data but poorly suited to complex, high-dimensional, or unstructured data
such as images, audio, text, genomic sequences, geospatial data, and social
relationship (like/follow) data.

Vector databases emerged to fill this gap: they store data as **high-dimensional
vectors**, enabling fast storage, retrieval, and analysis of complex data types
without heavy pre-processing.

```mermaid
flowchart LR
    A[Complex / Unstructured Data] --> B{Traditional DB?}
    B -- "Needs heavy pre-processing<br/>Poor similarity search" --> C[Relational Tables]
    A --> D{Vector DB}
    D -- "Native fit" --> E[High-Dimensional Vectors]
    E --> F[Fast storage, retrieval & analysis]
```

## 2. What Companies Use Vector Databases For

Vector databases act as **libraries** that let companies:

- Find information (search)
- Mine data
- Teach computers to learn (ML/AI)

They organize data points in a **multi-dimensional space** based on proximity,
enabling analytical tasks such as:

```mermaid
mindmap
  root((Vector DB<br/>Analytical Tasks))
    Grouping items
      Clustering similar data
    Classifying items
      Assigning categories
    Suggesting relationships
      Recommendations
      Similarity links
```

## 3. Key Characteristics

### 3.1 Handling Complex Data Types

Vector databases natively handle data that traditional systems struggle with:

```mermaid
flowchart TD
    VDB[Vector Database] --> Rel[Relationship Data<br/>e.g. social likes]
    VDB --> Geo[Geospatial Data]
    VDB --> Gen[Genomic Data]
    VDB --> Img[Images]
    VDB --> Snd[Sounds]
    VDB --> Txt[Text Files]
    VDB --> Pat[Pattern Data]
```

### 3.2 Similarity Search

Vector databases quickly and accurately locate **related items** by measuring
the **proximity** of vectors in high-dimensional space. This is called a
**similarity search**.

```mermaid
flowchart LR
    Q[Query Vector] --> S[Similarity Search]
    S --> N1[Nearest Neighbor 1]
    S --> N2[Nearest Neighbor 2]
    S --> N3[Nearest Neighbor 3]
    style Q fill:#f9f,stroke:#333
```

Used for:

- Finding similar images / sounds
- Recommendation systems (products, content, connections)
- Genetic analysis

### 3.3 Performance at Scale

Vector databases rely on:

- **Distributed computing**
- **Indexing**
- **Parallel processing**

to manage big datasets and process queries quickly.

```mermaid
flowchart TD
    A[Large Dataset] --> B[Indexing]
    A --> C[Distributed Computing]
    A --> D[Parallel Processing]
    B --> E[Fast Query Response]
    C --> E
    D --> E
```

### 3.4 Industry Applications

```mermaid
flowchart LR
    VDB((Vector<br/>Database)) --> Bio[Biology /<br/>Climate Analysis]
    VDB --> Health[Healthcare /<br/>Patient Outcomes]
    VDB --> Ecom[E-commerce /<br/>Product Recommendations]
    VDB --> Social[Social Media /<br/>Connection Suggestions]
    VDB --> Traffic[Traffic Planning /<br/>Traffic Analysis]
```

### 3.5 Role in Machine Learning & AI

Vector databases are a **natural way to store and explore ML data**. They
integrate easily into ML pipelines and accelerate the development and
release of AI-powered applications.

```mermaid
flowchart LR
    Data[Raw Data] --> Embed[Embedding Model]
    Embed --> Vec[Vector Representation]
    Vec --> VDB[(Vector Database)]
    VDB --> Pipeline[ML / AI Pipeline]
    Pipeline --> App[AI-Powered App]
```

## 4. What Is a Vector?

A **vector** is a mathematical object defined by **size (magnitude)** and
**direction**. In a vector database, a vector is an **array of numerical
values**, where each number (dimension) represents a feature or attribute
of the data point.

```mermaid
flowchart LR
    subgraph Vector["Vector = [Genre, Pages, Year, Rating]"]
        D1["Dim 1: Genre"]
        D2["Dim 2: Pages"]
        D3["Dim 3: Publication Year"]
        D4["Dim 4: Avg Rating"]
    end
```

Vectors can represent: images, sounds, text files, pattern data, map data,
genomic information, and more.

## 5. Worked Example — Books as Vectors

Encoding scheme: `[genre, pages, publication_year, avg_rating]`
Genre codes: `1 = fiction`, `2 = non-fiction`, `3 = science fiction`

| Book Type       | Genre | Pages | Year | Rating |
|-----------------|:-----:|:-----:|:----:|:------:|
| Fiction         | 1     | 350   | 2003 | 4.5    |
| Non-fiction     | 2     | 250   | 2015 | 4.8    |
| Science fiction | 3     | 400   | 1990 | 4.2    |

```mermaid
flowchart TD
    Book[Book] --> V["Vector: [genre, pages, year, rating]"]
    V --> F["Fiction: [1, 350, 2003, 4.5]"]
    V --> N["Non-fiction: [2, 250, 2015, 4.8]"]
    V --> S["Sci-fi: [3, 400, 1990, 4.2]"]
```

### 5.1 Similarity Search in Action

**Goal:** Find science fiction books with ~200 pages and a rating between
4.7 and 5.0.

Candidate science fiction books (genre = 1 in this sub-list):

| Book   | Genre | Pages | Year | Rating |
|--------|:-----:|:-----:|:----:|:------:|
| Book 1 | 1     | 180   | 2010 | 4.6    |
| Book 2 | 1     | 220   | 2005 | 4.8    |
| Book 3 | 1     | 210   | 2015 | 4.9    |
| Book 4 | 1     | 190   | 2018 | 4.7    |
| Book 5 | 1     | 200   | 2012 | 4.5    |

```mermaid
flowchart LR
    Query["Query: ~200 pages,<br/>rating 4.7–5.0"] --> Search[Similarity Search<br/>over vector space]
    Search --> B2["Book 2: 220 pages, 4.8 ✅"]
    Search --> B3["Book 3: 210 pages, 4.9 ✅"]
    Search --> B4["Book 4: 190 pages, 4.7 ✅"]
    Search --> B1["Book 1: 180 pages, 4.6 ❌ (rating too low)"]
    Search --> B5["Book 5: 200 pages, 4.5 ❌ (rating too low)"]
```

Instead of scanning the **entire platform**, the vector database narrows the
search using proximity in vector space — faster and more relevant than a
full linear search.

## 6. Summary

```mermaid
mindmap
  root((Vector Databases))
    Purpose
      Simplify storage, organization, retrieval
      Handle complex/unstructured data
    Core Concept
      Data stored as high-dimensional vectors
      Vector = array of numerical features
    Capabilities
      Similarity search
      Grouping / Classification
      Relationship suggestions
    Performance
      Distributed computing
      Indexing
      Parallel processing
    Applications
      Machine learning & AI pipelines
      Healthcare, e-commerce, social media
      Traffic planning, genomics, climate analysis
```

**Key takeaways:**

1. Vector databases store data as high-dimensional vectors, not tables.
2. Each vector is an array of numbers representing features/attributes of a data point.
3. Similarity search finds related items based on proximity in vector space.
4. They scale via distributed computing, indexing, and parallel processing.
5. They are foundational infrastructure for modern ML/AI applications.
