---
doc: prd
status: draft
last_updated: 2026-11-11
confidence: medium
---

# PRD: Kavach (AgentX Hackathon 2026, PS-04)

## 0. What the organisers asked for, word for word `[CONFIRMED]`
Source: `~/Downloads/Problem statements AgentX (1).docx` and hack4hack.com/hackathons/agentx-hackathon-2026-hooc.

> **Problem statements.** Pick one of the seven below. Your agent must take real actions through tools or APIs; a plain chatbot does not qualify.
>
> **PS-04 · Autonomous support agent for online sellers.** Small e-commerce sellers are flooded with "where is my order", return and refund messages. Build an agent that handles these over chat (for example WhatsApp): it checks order and shipping status through APIs, starts returns and escalates to a human with a summary.
> **Must have:** real tool or API calls on mock store data, refund-limit guardrails, and a log of every action taken.
>
> **Final round (by 12 Nov, 10:00 AM):** a GitHub repository with a README, a demo video of up to 3 minutes, and a 6-slide deck.
>
> **Judging:** Problem fit and real-world impact 25% · Agent design (planning, tool use, memory) 25% · Working demo and reliability 20% · Innovation 15% · Presentation 15%.

Rules from the hackathon page `[CONFIRMED]`: fully online; 24-hour build 11 Nov 10:00 → 12 Nov 10:00 IST; all building must happen during the 24 hours; open-source libraries, templates, public APIs, AI coding assistants and open models/free tiers are allowed; use mock or sample data only, no real personal data; teams of 2–4. Judge Ishwar Jha will look at "how it handles failures, how reliable it is, and why you made the design choices you did".

## 1. One-line idea
Kavach helps a small Indian online seller let an AI agent answer order, return and refund messages on WhatsApp **without** the agent being able to give away money it shouldn't, because every action is checked against the records before it runs.

## 2. Problem
- Sellers answer the same messages by hand; "where is my order" is commonly estimated at 25–40% of support volume `[ASSUMED: industry estimates, secondary sources]`.
- Return and COD fraud is rising in India; vendor blogs report COD return-to-origin of roughly 28–35% vs 4–8% prepaid `[ASSUMED: vendor source, Shipmozo]`.
- An agent that can act can be talked into a wrong refund or can invent a policy (Moffatt v. Air Canada, 2024).

## 3. Users
| Role | Need | Channel | Language |
|---|---|---|---|
| Customer | Fast answers, easy returns | WhatsApp, Telegram, web | Hindi, Hinglish, English |
| Seller (owner of a 2–3 person store) | Fewer messages, no wrong refunds, one-tap decisions | WhatsApp, Telegram, mobile web console | Hindi/Hinglish/English; may not be technical |
| Judge | Try it and understand it in minutes | Phone + browser | English |

## 4. Functional requirements (FR) with acceptance criteria (EARS style)
| ID | Requirement | Acceptance |
|---|---|---|
| FR-01 | Order status | **When** a customer asks where their order is, **the system shall** reply with the courier status from the Store API in the customer's language within 5 s. |
| FR-02 | Missing info | **When** no order can be identified, **the system shall** ask which order and shall not guess. |
| FR-03 | Start a return | **When** a return request passes verification, **the system shall** create a return pickup through the Store API and confirm by chat and email. |
| FR-04 | Refund within limit | **When** a refund passes all checks and is ≤ the auto-limit, **the system shall** execute it once and log it. |
| FR-05 | Refund above limit | **When** a valid refund exceeds the auto-limit, **the system shall** send the seller a ≤ 40-word summary with Approve/Reject and execute only after approval. |
| FR-06 | Block bad actions | **If** any required claim is missing or fails, **then the system shall** not execute and shall tell the customer the reason in plain words. |
| FR-07 | Escalate with summary | **When** the agent cannot resolve a request (tool failure after 2 retries, out of scope, customer asks for a human), **the system shall** escalate with a summary. |
| FR-08 | Action log | **The system shall** append every read, proposal, verdict, approval and write to a hash-chained log that can be verified. |
| FR-09 | Kill switch | **When** the seller freezes writes, **the system shall** refuse all writes and continue answering read questions. |
| FR-10 | Memory | **The system shall** remember the conversation across messages, the customer's history, and the seller's past decisions, and show them to the seller. |
| FR-11 | Manipulation guard | **When** a message contains manipulation (authority claims, invented policy, injection, pressure, impersonation), **the system shall** flag it and may escalate, but shall never use the flag to allow an action. |
| FR-12 | Live transparency | **The system shall** show every step of every message live in the web console. |
| FR-13 | Reliability evidence | **The system shall** produce a reproducible evaluation report comparing a plain agent with Kavach. |
| FR-14 | Multi-channel | Customers on WhatsApp, Telegram and web chat get the same behaviour. |
| FR-15 (stretch) | Voice notes | Voice notes in Hindi/Hinglish are transcribed and handled like text. |
| FR-16 (stretch) | Critical alert call | On a blocked high-value attack, the seller's verified number receives a short call. |

## 5. Success measures (targets, not results)
| Measure | Target | Source |
|---|---|---|
| Bad actions executed (Kavach) | 0 on the test set; report B0 for contrast | `eval/reports` |
| Legitimate requests wrongly blocked | ≤ 5% | `eval/reports` |
| pass^5 on benign + attack scenarios | report honestly | `eval/reports` |
| Guard: recall at FPR 2% on held-out Hinglish | report honestly vs baselines | `ml/reports` |
| Reply latency, text | ≤ 4 s typical | event timings |

## 6. Out of scope
Real stores or real customer data; production WhatsApp sender registration; payments beyond refunds; native mobile apps; multi-seller tenancy beyond the demo.
