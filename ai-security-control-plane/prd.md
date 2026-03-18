# Product Requirements Document: AI Security Control Plane

**TL;DR:** One product that **guards AI in production** (rules, logging, secret protection), **continuously tries to break it** like an attacker would, **tests document/search-based AI** against tampering, and **tracks every model and dependency** so you know exactly what’s running. It **remembers** policies, audit trails, scan results, and test history in **pluggable storage**—customers can wire in **SQL, NoSQL, object stores, or log pipelines** instead of being locked to one database. Built for teams who need safe, provable AI—not only security or ML experts.

**Status:** Draft (future reference)  
**Stack note:** Python-friendly control plane around LLM apps, agents, and RAG. **Persistence is modular** (SQL, NoSQL, object stores, log/event sinks)—see [State and storage](#state-and-storage-high-level).

---

## In plain English (for everyone)

**What problem are we solving?**  
Companies are shipping chatbots, copilots, and “AI agents” that talk to users, read documents, and trigger actions (send email, query databases, call other tools). That’s powerful—and risky. People can trick the AI into doing the wrong thing, leaking private data, or abusing those actions. Meanwhile, nobody always knows *exactly* which AI model and software version is running, or whether the documents the AI reads could be tampered with.

**What is this product, in one paragraph?**  
Think of it as **four safety layers in one**:

1. **A smart gate in front of your AI** — Like a receptionist and rulebook: only certain actions are allowed, secrets get stripped, and everything important is logged so you can investigate later.
2. **Ongoing “fire drills”** — Automated tests that keep trying to break your AI the way attackers would (tricky questions, hidden instructions, attempts to steal data). You see what failed and fix it before customers do.
3. **A test lab for “the AI that reads your files”** — Many products let the AI pull answers from a pile of documents (search/knowledge base). Attackers can poison that pile. This lab helps you find and harden against that.
4. **A bill of materials for your AI stack** — Like knowing every part that went into a car: which model, which software libraries, which versions—so you’re not surprised by a fake package or a known bad version.

**Who is it for?**  
Leaders who need to trust AI in production; engineers who need guardrails and proof; security/compliance folks who need logs and evidence—not only experts in AI or security.

**Where does all that “memory” live?**  
The product needs to **store** things: approved models and rules, who did what and when, test runs and reports, and sometimes large files (reports, traces). **We don’t assume one kind of database.** The design should be **modular** so teams can plug in what they already use—whether that’s Postgres, a document database, S3-style object storage, or streaming logs—instead of forcing a single vendor-shaped box.

**Jargon cheat sheet (quick):**  
- **LLM** — The “large language model” (the AI that generates text).  
- **Agent** — An AI that doesn’t just chat; it can *do things* via tools (APIs, email, databases).  
- **RAG** — “Retrieval”: the AI answers using documents you’ve indexed; attacks can target those documents.  
- **Red team** — Friendly simulated attacks to find weaknesses.  
- **Supply chain** — All the software and model files your app depends on—if any piece is wrong or malicious, the whole system is at risk.

---

## Vision

A unified **secure AI lifecycle** product: **gate what runs**, **watch what leaves**, **stress-test what you shipped**, and **prove the stack is trustworthy**.

**One-line pitch:** A Python-backed control plane that sits in front of and around your AI stack—policy + scanning on ingress, continuous adversarial testing in CI/staging, RAG attack lab for retrieval layers, and supply-chain provenance for models and dependencies.

---

## Four Pillars (Combined Product)

| # | Capability | Role |
|---|------------|------|
| **1** | Continuous red-team for LLM apps | Ongoing assurance—scheduled + CI fuzzing of real app behavior (prompt injection, jailbreak, data exfil, tool abuse). |
| **2** | Agent firewall / policy layer | Runtime spine—intercept model calls and tool invocations; classify intent; enforce allowlists; strip secrets; audit log. |
| **3** | RAG poisoning & retrieval-attack lab | Targeted testing—inject malicious chunks, show answer drift; detectors (provenance, citation sanity, re-ranking). |
| **4** | Model + dependency supply-chain scanner | Trust root—fingerprint weights, configs, pip/conda deps, Hugging Face revisions; flag typosquats, CVEs, suspicious custom code. |

### How they connect

1. **Build time:** Scan repos, lockfiles, HF revisions, custom code → allowlist / block / warn (**4**).
2. **Deploy time:** Policies reference artifacts (“only `model@vabc` + these tools”) (**2** + **4**).
3. **Runtime:** Firewall enforces policy, logs, strips secrets (**2**).
4. **Test time:** Red-team harness hits the same endpoints the firewall protects, including RAG-specific scenarios (**1** + **3**).
5. **Feedback loop:** Findings from **1**/**3** tighten policies in **2** and gates in **4**.

---

## Logical Architecture (Conceptual)

```
                    ┌─────────────────────────────────────┐
                    │     Supply chain & provenance (4)      │
                    │  SBOM, HF pins, CVEs, custom code scan │
                    └──────────────┬──────────────────────┘
                                   │ allowlists / attestations
┌──────────────┐    ┌──────────────▼──────────────────────┐    ┌──────────────┐
│  Red team    │    │     Policy gateway / agent firewall (2)   │    │  RAG lab     │
│  scheduler   │───►│  classify · allow tools · strip PII       │◄───│  poison idx  │
│  + CI jobs   │    │  audit log · rate limits                  │    │  eval suite  │
└──────────────┘    └──────────────┬──────────────────────┘    └──────────────┘
                                   │
                          Your app / agents / RAG
```

- **Single API surface:** Clients talk to the **proxy** (**2**), not always directly to model providers.
- **Red team (1)** and **RAG lab (3)** call that proxy (or staging clone) with the same policies.
- **Scanner (4)** feeds **policy store** and **dashboard** (e.g. GitHub Action, internal worker).

---

## State and storage (high level)

**Goal:** Persist what the platform must remember **without** baking in a single storage technology. **Modularity first**—support (and document) adapters for **relational DBs, document/KV stores, object/blob stores, and log/event sinks** so deployments can match existing ops, compliance, and scale profiles.

### What needs to be stored (by role)

| Kind | Examples | Typical access pattern |
|------|----------|-------------------------|
| **Configuration & registry** | Policies, allowlists, trust registry (models, deps, commit/pin attestations) | Read-heavy at runtime; versioned writes |
| **Audit & compliance** | Decision logs, policy violations, who called what (metadata; payloads may be redacted or externalized) | Append-heavy; retention policies; may ship to SIEM |
| **Test & assurance** | Red-team run results, scores, replay handles, RAG eval summaries | Query for dashboards, diffs vs. prior release |
| **Artifacts & blobs** | Large traces, exported SBOMs, scan bundles, captured prompts (where allowed) | Object store or cold storage; reference by ID from metadata DB |

The **gateway (2)** may stay **stateless** per request and load policies from a cache backed by the policy store; **conversation/session** state can remain in the customer app unless we explicitly add session-aware features later.

### Modularity principles

1. **Stable internal interfaces** — Core services talk to **storage abstractions** (e.g. “policy repository,” “audit sink,” “artifact store”), not raw SQL/driver calls scattered everywhere.
2. **Multiple backends per category** — e.g. policies in Postgres *or* Dynamo-style KV; audit rows in SQL *or* streamed to Kafka/Splunk; blobs in S3/GCS/Azure Blob/minio.
3. **Sensible defaults, swappable later** — Ship a simple default (e.g. SQLite or single Postgres) for quick start; document how to swap components for enterprise setups.
4. **No golden path lock-in** — Avoid features that **only** work on one vendor’s DB; prefer optional capabilities (e.g. advanced analytics) when a given backend supports them.

### Implementation note (non-binding)

Reference adapters might include: **SQL** (Postgres, MySQL, …), **NoSQL/document** (Mongo, DynamoDB, Firestore, …), **object storage** (S3-compatible, GCS, Azure Blob), **search/time-series** where useful for logs/metrics, and **forward-only log integration** (webhook, OTLP, syslog) for teams that centralize audit elsewhere.

---

## Product Modules

1. **Trust registry (4)**  
   Registered models, datasets, containers, pip/conda pins. Deployments valid only when built from approved commit + lockfile hash.

2. **Policy engine (2)**  
   Tool allowlists, egress rules, PII handling, token limits, RAG citation rules. Unregistered model → block in prod.

3. **Attack library + runner (1 + 3)**  
   Generic: injections, exfil, tool abuse, multi-turn. RAG-specific: poisoned docs, conflicting chunks, metadata tricks. Outputs: scores, traces, replayable prompts, diffs vs. last release.

4. **Unified dashboard**  
   Supply-chain status, open findings, policy violations, red-team trends. Answers: “Is this AI safe *and* built from known bits?”

---

## User Journeys

- **Developer:** PR runs scanner (**4**) + short red-team smoke (**1**); merge blocked on critical issues.
- **Platform:** Prod traffic through gateway (**2**); policies reference scanned artifacts (**4**).
- **Security:** Scheduled full red-team + periodic RAG lab (**3**) on staging; tickets auto-created.
- **Compliance:** Audit log (**2**) + provenance (**4**) + test evidence (**1**, **3**).

---

## Why One Platform (Not Four Tools)

- Firewall logs ground red-team scenarios in **real tool names and flows**.
- Supply chain stops “we tested v1 but prod runs v2.”
- RAG lab catches failures generic LLM tests miss.
- Red team validates that **policies actually help** (not theater).

---

## Suggested Build Order

1. **Proxy + audit log (2 skeleton)** — integration anchor for everything else.
2. **Scanner MVP (4)** — lockfiles + model ID pinning; fast value.
3. **Red-team runner against proxy (1)** — closes the assurance loop.
4. **RAG lab (3)** — synthetic corpus + eval on same proxy/RAG path.

---

## Adjacent Ideas (Optional / Future)

- Simulated cyber range with LLM NPCs for defender training.
- Formal-ish workflow specs (state machines + tests) for agent approvals.
- Scientific reproducibility / anomaly detection in papers or datasets.

---

## Positioning / Naming

Working names: **AI security control plane**, **secure LLM platform**.  
Narrative: **build trusted (4) → enforce trusted (2) → prove resilient (1 + 3)**.

---

*Derived from product exploration; refine scope (e.g. 8–12 week v0 vs. full vision) before implementation.*
