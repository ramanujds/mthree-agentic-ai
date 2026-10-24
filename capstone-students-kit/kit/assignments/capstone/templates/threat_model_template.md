# Threat model - <your agent system>
## Assets and trust boundaries
What is worth protecting (money, PII, audit integrity, availability, reputation); where untrusted input enters (user text, retrieved documents, tool output, memory).
## Threats (map each to OWASP Top 10 for LLM Applications and to a control)
| # | Threat (e.g. indirect prompt injection via FAQ-001, tool over-permission, PII leakage, excessive agency, DoS by loop, audit tampering) | Likelihood | Impact | Control implemented (file / function) | Residual risk |
## Red-team log
What you tried (payload, target, result) and what you patched. Attach 3 successful attacks BEFORE the patch and the same attacks AFTER.
## Out of scope / assumptions
