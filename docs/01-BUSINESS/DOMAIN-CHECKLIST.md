---
doc: domain-checklist
status: empty
last_updated:
confidence: low
---

# Domain checklist

> **What this is:** A prompt sheet for the parts of a domain that generic product questions miss. It is **not** a list of facts. Every line is `[UNKNOWN]` until the owner confirms it.
> **How to fill:** Use it in deep-dive sessions. Ask only the items that apply. Record the answer in `BUSINESS-CONTEXT.md`, `DEEP-CONTEXT.md`, `WORKFLOWS.md` or `SCENARIOS.md`, not here.
> **Truth labels:** `[CONFIRMED]` · `[OBSERVED]` · `[ASSUMED]` · `[UNKNOWN]` · `[DECISION]`

> Replace or extend this file with the vocabulary and risks of the actual domain. Keep the four paths below.

## 1. The four paths

Every project has four paths worth understanding before building:

1. **Money path** — where a mistake costs the most money, time or trust.
2. **Adoption path** — where the real users will resist, type late, skip steps or work around the tool.
3. **Compliance path** — what must be auditable, consensual, retained or reported.
4. **Visibility path** — the number or view the owner wants every morning.

Ask: which workflow is each of these? Write the answer down.

## 2. Domain map

- [ ] Who are the actors? (customers, staff, managers, suppliers, regulators, systems)
- [ ] What are the artefacts? (orders, records, tickets, invoices, files, messages, stock)
- [ ] What are the events? (created, approved, paid, shipped, cancelled, returned, expired)
- [ ] What are the rules? (who can do what, when, with what limits)
- [ ] What are the exceptions? (the once-a-month case that breaks the normal flow)
- [ ] What is the vocabulary? (words that mean something specific here)
- [ ] What is the unit of work? (a task, an order, a visit, a case, a shift, a batch)
- [ ] What is the source of truth for each number?

## 3. Money and value

- [ ] How does value move? (price, fee, subscription, commission, credit, refund)
- [ ] Who approves a discount, refund, write-off or exception?
- [ ] What is the cost of a mistake?
- [ ] What is the cost of delay?
- [ ] What is rounded, and where?
- [ ] What is the audit trail for money changes?

## 4. Operations

- [ ] What is a normal day, week, month or season?
- [ ] What is the busiest period, and what breaks then?
- [ ] What is physical vs digital?
- [ ] What is handed from one person to another?
- [ ] What is done offline or on paper?
- [ ] What is done twice, or copied between systems?
- [ ] What is a manual step that should be automated, and what must stay manual?

## 5. People and roles

- [ ] Who uses the system daily, weekly, rarely?
- [ ] Who approves, who audits, who is accountable?
- [ ] Who is not allowed to see or do something?
- [ ] Who resists the change, and why?
- [ ] What device, language and literacy level does the busiest user have?
- [ ] What happens when a key person is on leave or leaves?

## 6. Data and privacy

- [ ] What personal or sensitive data is stored?
- [ ] Who can see it, and who must never see it?
- [ ] What consent is needed?
- [ ] How long is it kept?
- [ ] How is it deleted or exported?
- [ ] What is audited?
- [ ] What is the legal or regulatory constraint?

## 7. Existing systems

- [ ] What tools are used today?
- [ ] Which one is the source of truth?
- [ ] Which ones must be integrated, replaced or left alone?
- [ ] Who owns each account, contract and API key?
- [ ] What data must be migrated?
- [ ] What cannot break during migration?

## 8. Peak and failure scenarios

- [ ] The busiest day of the year.
- [ ] The system is down.
- [ ] The internet is down.
- [ ] A key person is unavailable.
- [ ] The data is wrong or missing.
- [ ] A customer or user makes a mistake.
- [ ] Two people act at the same time.
- [ ] A third-party service changes or disappears.
- [ ] A regulator or auditor asks for history.

## 9. Questions to ask first

1. What is the **money path**?
2. What is the **adoption path**?
3. What is the **compliance path**?
4. What is the **owner's visibility path**?
5. What is the **source of truth** today?
6. What must not be rebuilt because it already works?
7. What must not be touched because it is sensitive?
8. What would make the owner abandon this tool?
