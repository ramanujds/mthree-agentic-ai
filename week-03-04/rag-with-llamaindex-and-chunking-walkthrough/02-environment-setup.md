# Step 1 — Environment Setup

> [Back to index](README.md) · Previous: [Overview and Concepts](01-overview-and-concepts.md) · Next: [Shared Scaffolding](03-shared-scaffolding.md)

## Goal

Get Ollama and Chroma running, and scaffold a `uv` project with the sample document all six scripts will share.

## Why this matters

Ollama (for the LLM and embedding model) and Chroma (for the vector store) are the same two services every LlamaIndex + Chroma example in this repo depends on — there's nothing chunking-specific about installing them. [simple-rag-example-chromadb-walkthrough's Step 1](../rag-with-LlamaIndex/simple-rag-example-chromadb-walkthrough/02-environment-setup.md) already covers installing Ollama, pulling models, and understanding why `IS_PERSISTENT=TRUE` matters for Chroma, in full. If you haven't done that before, go do steps 1 and 2 of that walkthrough now, then come back here.

What's actually new for *this* project: a `docker-compose.yml` with a different container name (so it doesn't collide with that other example if both happen to be running), and — more importantly — a single sample document rich enough to make six different chunking strategies actually look different from each other. A two-paragraph toy document would produce nearly identical chunks no matter which splitter you used; you need enough real structure and length for the strategies to disagree.

## 1. Start Chroma via Docker

```bash
mkdir rag-with-llamaindex-and-chunking && cd rag-with-llamaindex-and-chunking
```

```yaml
services:
  chromadb:
    image: chromadb/chroma:latest
    container_name: chunking-examples-chromadb
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/data
    environment:
      - IS_PERSISTENT=TRUE
      - ANONYMIZED_TELEMETRY=FALSE

volumes:
  chroma_data:
```

Save this as `docker-compose.yml`, then start it:

```bash
docker compose up -d
```

Verify it's up:

```bash
curl http://localhost:8000/api/v2/heartbeat
```

You should get a JSON response with a timestamp, not a connection error. If you already have another example's Chroma container bound to port 8000, stop it first (`docker compose down` in that folder) or change the `"8000:8000"` mapping here.

## 2. Scaffold the Python project

```bash
uv init --no-workdir --python 3.13 .
uv add "chromadb>=0.5.0" "llama-index-core>=0.14.24" "llama-index-embeddings-ollama>=0.10.0" "llama-index-llms-ollama>=0.11.0" "llama-index-vector-stores-chroma>=0.4.0"
```

## 3. Create the sample document

```bash
mkdir data
```

Save the following as `data/employee_handbook.md`. It's an invented company handbook with six clearly-headed sections — long and varied enough that fixed-size chunking, semantic chunking, and header-based chunking will each carve it up differently:

```markdown
# Acme Corp Employee Handbook

## Remote Work Policy

Employees may work remotely up to 3 days per week, subject to manager approval. Requests must be submitted at least 2 business days in advance through the HR portal. Fully remote arrangements are only available to employees in roles explicitly designated as remote-eligible by their department head.

Managers may temporarily suspend remote work privileges for a team during periods of critical project delivery, but must give at least 5 business days' notice before doing so. Employees on a performance improvement plan are required to work on-site for the duration of the plan, regardless of their normal remote work arrangement.

Equipment for remote work, such as monitors and ergonomic chairs, can be requested through the Facilities portal and is subject to a $500 annual budget per employee.

## Vacation Policy

All full-time employees accrue 18 days of paid vacation per year, accrued monthly at a rate of 1.5 days. Unused vacation days can be carried over to the next year, up to a maximum of 5 days; any unused balance beyond that cap is forfeited at year-end unless local law requires otherwise.

Vacation requests must be submitted at least 1 week in advance through the HR portal and require manager approval. During the last two weeks of December, no more than 30% of any single team may be on vacation simultaneously, to ensure adequate coverage.

Part-time employees accrue vacation on a pro-rated basis according to their contracted hours. Employees who leave the company are paid out for any unused, accrued vacation days as part of their final paycheck.

## Expense Reimbursement

Employees can be reimbursed for business-related expenses such as travel, client meals, and conference fees. Receipts must be submitted within 30 days of the expense through the Expense system; expenses submitted after 30 days require VP-level approval to be processed.

Reimbursements are processed within 10 business days of approval and are paid out via direct deposit on the next regular payroll cycle. Client meal reimbursements are capped at $75 per person, and alcohol is only reimbursable when accompanying a client and does not exceed 20% of the total meal cost.

International travel expenses must be submitted in the local currency along with the exchange rate used, and require pre-approval from both the employee's manager and Finance for any single trip exceeding $2,000.

## Onboarding

New hires receive a laptop on their first day, shipped by the IT department to their home address or delivered to their desk for office-based roles. If the laptop hasn't arrived by day 2, the new hire should contact it-support@example.com immediately so a loaner can be issued.

A new hire's email account is created automatically before their start date, and a welcome message with setup instructions is sent to their personal email one week prior. Access to Slack, the HR portal, and internal wikis is granted within the first 24 hours of the start date.

Every new hire is assigned an onboarding buddy, who reaches out on the first day to help with initial questions and introductions. If the new hire hasn't heard from their buddy by 10am on day one, they should contact their manager directly. The onboarding buddy program runs for the new hire's first 30 days, with a mandatory check-in at the two-week mark.

## Code of Conduct

All employees are expected to treat colleagues, clients, and partners with professionalism and respect. Harassment, discrimination, or retaliation of any kind will not be tolerated and should be reported immediately to HR or through the anonymous ethics hotline.

Conflicts of interest, including outside employment, financial interests in competitors, or personal relationships with direct reports, must be disclosed to HR as soon as they arise. Failure to disclose a known conflict of interest is grounds for disciplinary action, up to and including termination.

Confidential company information, including unreleased product plans, financial results, and customer data, must not be shared outside the company or with employees who do not have a legitimate business need to know.

## IT Security Policy

All company devices must have disk encryption and endpoint security software enabled before they can connect to internal systems; IT enforces this automatically for company-issued laptops. Employees must not install unapproved software on company devices without submitting a request through the IT portal.

Passwords for internal systems must be at least 14 characters, rotated every 180 days, and must not be reused across the last 10 passwords. Multi-factor authentication is required for all systems that handle customer data or financial information.

Any suspected security incident, including a lost device, phishing email, or unauthorized access, must be reported to the Security team within 1 hour of discovery. Delayed reporting of a known incident is treated as a policy violation independent of the incident itself.
```

Notice the shape: six `##` sections, each 2-3 paragraphs, each with a mix of simple facts ("18 days of paid vacation") and facts that need a nearby sentence for context (the alcohol reimbursement rule, which only makes sense next to the $75 cap it modifies). That mix is what will make the upcoming strategies disagree with each other.

## Try it

```bash
uv sync
```

This should resolve and install without errors. Then confirm both services are reachable:

```bash
curl http://localhost:11434
curl http://localhost:8000/api/v2/heartbeat
```

The first should print `Ollama is running`; the second should return a JSON heartbeat.

## Common mistakes

| Symptom | Cause | Fix |
| --- | --- | --- |
| `curl: (7) Failed to connect` on port 8000 | Chroma container isn't running, or another container already holds port 8000 | `docker compose ps`; if another project's Chroma is running, stop it or edit the port mapping here |
| `curl http://localhost:11434` connection refused | Ollama isn't running | Start the Ollama desktop app or run `ollama serve` |
| Models not pulled | Skipped the sibling walkthrough's model-pull step | `ollama pull llama3:8b && ollama pull nomic-embed-text` |
| `uv sync` fails resolving `llama-index-vector-stores-chroma` | Typo in the version constraint, or an unreachable package index | Re-check the `uv add` command above against `pyproject.toml` |

Next: **[Shared Scaffolding](03-shared-scaffolding.md)** — build the `common.py` module all six scripts import.
