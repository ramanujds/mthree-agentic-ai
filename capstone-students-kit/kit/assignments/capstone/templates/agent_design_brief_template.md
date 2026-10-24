# Agent Design Brief - <process name>
Case chosen (A / B / C from data/stakeholder_interviews/): ...        Author: ...        Date: ...

## 1. Problem statement
Who suffers, what is the current process, what does it cost (time / money / risk)? Quote the interview. Separate facts from assumptions.

## 2. Open questions and contradictions found in the interview
List at least 3 things the stakeholder said that are unclear, unmeasured, contradictory or not allowed, and how you would resolve each.

## 3. Proposed agent scope
What the agent does / what it must NOT do (out of scope). Which steps are automated, which are assisted, which stay human.

## 4. Inputs and outputs
Data in (with sensitivity), tools / systems it needs, outputs and who consumes them.

## 5. Success criteria
3-5 MEASURABLE criteria with a target and how it will be measured (baseline first!). Include quality, speed, safety.

## 6. Risk flags and controls
Table: risk | likelihood | impact | control | owner. Cover: wrong action, data leakage, over-reliance, regulatory/audit, prompt injection.

## 7. Human-in-the-loop design
Where a human approves / reviews, thresholds, escalation path.

## 8. Feasibility and recommendation
Architecture pattern (prompted LLM / RAG / tool agent / multi-agent) and why the simplest sufficient one. First pilot slice (2-4 weeks).
