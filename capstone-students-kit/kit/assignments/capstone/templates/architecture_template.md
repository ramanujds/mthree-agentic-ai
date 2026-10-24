# Architecture - <system name>
## Context
Business process, users, systems touched.
## Diagram
```mermaid
flowchart LR
  U[User] --> R[Router]
  R --> A[Retrieval agent] --> K[(Index / graph)]
  R --> T[Transaction agent] --> H{Human approval}
```
## Components and why
## Data flow and where PII is touched
## Failure modes and mitigations
## Decisions and alternatives rejected
