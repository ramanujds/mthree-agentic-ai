# Interview transcript - Case C: Wire exception handling
Interviewee: Ingrid Solberg, Head of Payments, Meridian Bank. Interviewer: you. (Synthetic case.)

**You:** What is an "exception" in your world?
**Ingrid:** A wire that cannot go straight through: wrong beneficiary details, missed cut-off, a name-screening hit, an amount above the sender's approval limit. About 150 a day.
**You:** Who handles them?
**Ingrid:** Six operators. Each one reads the wire, checks a few systems, and decides: fix and release, return to sender, or escalate. The reasons are written in free text, which makes reporting impossible.
**You:** What do you want automated?
**Ingrid:** Everything, ideally. The assistant should look at the exception, decide, and release the payment. If it saves a minute per case I am happy.
**You:** Even for large amounts?
**Ingrid:** Well, no, large ones need approvals, obviously. Dual control from $10,000. Our policy says so. Although for repeat customers we usually waive that.
**You:** Is that waiver written down?
**Ingrid:** It is how we have always done it.
**You:** What are the risks you worry about?
**Ingrid:** Paying the wrong person. Paying twice. Regulators asking "why did the system release this?" and nobody being able to answer.
**You:** What data does an operator look at?
**Ingrid:** The wire message, the customer profile, sanctions screening results, past wires to the same beneficiary.
**You:** Time pressure?
**Ingrid:** Domestic cut-off is 4 PM, international 1 PM. Between 3 and 4 it is chaos.
