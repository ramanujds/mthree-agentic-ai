# LangChain

LangChain is a Python/JS framework for building applications on top of LLMs.
It gives you standard interfaces for models, prompts, retrieval, memory, and
tools, plus a way to compose them into pipelines ("chains") using LCEL
(LangChain Expression Language — the `|` operator).

## Core components

### Chat Models / LLMs
Wrapper around a model provider (OpenAI, Anthropic, Bedrock, local models via
Ollama, etc.) with a consistent `.invoke()` / `.stream()` interface, so you
can swap providers without rewriting your app.

### Prompt Templates
Parameterized prompts (`ChatPromptTemplate`, `PromptTemplate`) — define a
prompt once with `{placeholders}` and fill them in at call time.

### Output Parsers
Convert the raw model response (a string, or tool-call JSON) into a typed
Python object — plain strings, JSON, or a Pydantic model via
`with_structured_output`.

### Document Loaders
Read data from a source (PDF, web page, CSV, database, Notion, etc.) into a
standard `Document` object (text + metadata).

### Text Splitters
Break long documents into chunks small enough to embed and fit into a
context window (e.g. `RecursiveCharacterTextSplitter`).

### Embeddings
Turn text into vectors for semantic search (`OpenAIEmbeddings`,
`HuggingFaceEmbeddings`, etc.).

### Vector Stores / Retrievers
Store embedded chunks and fetch the most relevant ones for a query
(Chroma, FAISS, Pinecone, pgvector, ...). A `Retriever` is the standard
interface for "given a query, return relevant documents."

### Memory
Carries conversation history between calls (simple buffer, summarized
history, or a persisted store) so a chat app can be multi-turn.

### Chains (LCEL)
Compose the pieces above into a pipeline with `|`:
`prompt | model | output_parser`. Chains support `.invoke()`, `.stream()`,
`.batch()`, and async variants automatically.

### Tools & Agents
A `Tool` is a Python function (with a name/description/schema) the model can
call. An agent lets the model decide which tool to call and loops until it
has an answer. (For anything beyond a simple loop, use LangGraph instead —
see [langchain-ecosystem.md](langchain-ecosystem.md).)

## Installation

```bash
pip install langchain langchain-anthropic
# or: pip install langchain langchain-openai
```

Set your API key as an environment variable, e.g. `ANTHROPIC_API_KEY` or
`OPENAI_API_KEY`.

## A very simple example

The minimal LangChain pattern: prompt → model → parser.

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

model = ChatAnthropic(model="claude-sonnet-5")

prompt = ChatPromptTemplate.from_template(
    "Explain {topic} in one sentence for a {audience}."
)

parser = StrOutputParser()

chain = prompt | model | parser

result = chain.invoke({"topic": "recursion", "audience": "5-year-old"})
print(result)
```

That's it — `chain.invoke(...)` fills the prompt template, sends it to the
model, and parses the response into a plain string.

## Step-by-step: build a simple RAG Q&A app

A slightly more realistic example — answer questions over your own documents.

### 1. Install dependencies

```bash
pip install langchain langchain-anthropic langchain-community chromadb
```

### 2. Load a document

```python
from langchain_community.document_loaders import TextLoader

loader = TextLoader("notes.txt")
docs = loader.load()
```

### 3. Split it into chunks

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)
```

### 4. Embed and store the chunks

```python
from langchain_community.vectorstores import Chroma
from langchain_anthropic import ChatAnthropic
from langchain_community.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Chroma.from_documents(chunks, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
```

### 5. Build the RAG chain

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

model = ChatAnthropic(model="claude-sonnet-5")

prompt = ChatPromptTemplate.from_template(
    "Answer the question using only this context:\n{context}\n\nQuestion: {question}"
)

def format_docs(docs):
    return "\n\n".join(d.page_content for d in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | model
    | StrOutputParser()
)
```

### 6. Ask a question

```python
answer = rag_chain.invoke("What did I write about deadlines?")
print(answer)
```

At each `invoke`, the chain: retrieves the top-3 relevant chunks →
formats them into the prompt → sends it to the model → parses the string
answer.

## When to reach for LangChain vs. something else

- Simple, single LLM call → a raw provider SDK call is often less code than
  a LangChain chain.
- RAG, prompt templating, swapping model providers → LangChain is a good fit.
- Multi-step agents, loops, multi-agent systems → use LangGraph on top of
  LangChain's model/tool abstractions.
