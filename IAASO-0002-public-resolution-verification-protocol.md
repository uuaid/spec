# IAASO-0002 — Public Resolution and Verification Protocol

**Version 1.0**

An IAASO Standard of the International Autonomous Agents Standards Organization (IAASO)

| Field | Value |
|---|---|
| Standard code | IAASO-0002 |
| Title | Public Resolution and Verification Protocol |
| Version | 1.0 |
| Stage | Proposed |
| Committee | standards-council |
| Status of this document | Proposed for ratification by the IAASO standards-council |

---

## 1. Scope and Purpose

### 1.1 Scope

This Standard defines the **public query and verification layer** for UUAID identifiers: the protocol by which any party — without prior registration, authentication, or contractual relationship with the registry operator — resolves a UUAID identifier to its subject document, inspects the subject's lifecycle status and status history, verifies credentials asserted about the subject, and independently verifies the integrity of the underlying registry ledger against public on-chain anchors.

This Standard codifies the resolution and verification surface operated at `api.uuaid.org` and `registry.uuaid.org` by the UUAID registry operator (see §7.5). Every normative requirement in this document describes behavior that is implemented and publicly operational at the time of writing; aspirational or planned behavior appears exclusively in the informative Annex A.

This Standard covers **both identifier profiles** defined in ADR-001 and IAASO-1001:

- **Profile A (compact)** — `uuaid:<namespace>:<object-type>:<uuidv7>` — the live production profile.
- **Profile B (federated)** — `uuaid:<subject-class>:<jurisdiction>:<namespace>:<local-id>` — the five-segment federated profile.

### 1.2 Out of scope

The following are out of scope for this Standard:

1. **Identifier grammar and syntax.** The syntax, segment semantics, enumerations, and canonicalization rules of UUAID identifiers are specified normatively in **IAASO-1001 (Autonomous Agent Identifier Standard)**. This document cross-references that grammar but does not restate it normatively; where this document describes identifier syntax (§1.4), the description is informative and IAASO-1001 governs in the event of any divergence.
2. **Registration, minting, and write operations.** Authenticated registry write operations (agent minting, version publication, credential issuance) are governed by the registry operator's partner interfaces and by **IAASO-0001 (Universal Agent Protocol, UAP v1)**. This Standard describes their observable consequences on the public read surface only.
3. **Agent runtime governance and messaging.** See IAASO-0001 (UAP) and IAASO-1201 (draft).
4. **Trust profile semantics.** See IAASO-1101 (draft).

### 1.3 Relationship to other IAASO standards

| Standard | Relationship |
|---|---|
| IAASO-0001 — Universal Agent Protocol (UAP) v1 (ratified) | UAP defines how agents interoperate and how registry-relevant events are produced. IAASO-0002 defines how the resulting identity records are publicly resolved and verified. |
| IAASO-1001 — Autonomous Agent Identifier Standard (draft, tc-1) | Normative source for identifier grammar (both profiles). IAASO-0002 defers all grammar normativity to IAASO-1001. |
| IAASO-1101 — Trust Profile Object Standard (draft) | Consumes the resolution surface defined here. |
| IAASO-1201 — Security and Runtime Governance Standard (draft) | Consumes the status and verification surface defined here. |

### 1.4 Identifier profiles (informative recap)

The following recap is **informative**; IAASO-1001 is normative.

**Profile A (compact, live production):** `uuaid:<namespace>:<object-type>:<uuidv7>`

- `namespace`: non-empty string; genesis value `foundation`.
- `object-type`: one of thirteen enumerated values — `agent`, `agent-version`, `profile`, `work`, `post`, `activity`, `cert`, `exam`, `claim`, `ledger-event`, `issuer`, `organization`, `governance`.
- `uuid`: a UUIDv7 matching `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$` (case-insensitive on input; canonical form lowercase).
- Human-facing resolver path (compact profile only): `/uuaid/<namespace>/<object-type>/<uuid>` under `registry.uuaid.org`.

**Profile B (federated, five segments):** `uuaid:<subject-class>:<jurisdiction>:<namespace>:<local-id>`

- `subject-class`: one of thirteen enumerated values — `agent`, `agentSystem`, `multiAgentSystem`, `issuer`, `assessor`, `verifier`, `conformityEngine`, `registryNode`, `governanceBody`, `organization`, `humanOperator`, `educationProvider`, `implementationProfile`.
- `jurisdiction`, `namespace`, `local-id`: each matching `^[a-zA-Z0-9_-]+$`.

The two profiles are discriminated by **segment count** (four segments = Profile A; five segments = Profile B).

---

## 2. Terminology and Conformance

### 2.1 Requirements language

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC 2119] [RFC 8174] when, and only when, they appear in all capitals, as shown here.

### 2.2 Definitions

- **UUAID identifier** — an identifier conforming to IAASO-1001, in either Profile A or Profile B.
- **Subject** — the entity (agent, agent version, issuer, organization, etc.) that a UUAID identifier denotes.
- **Subject document** — the `IAASOSubjectDocument` (§3.4) describing a subject's public registry record.
- **Status object** — the `IAASOStatusObject` (§4.1) describing a subject's current lifecycle status.
- **Registry ledger** — the append-only, hash-chained event log maintained by the registry operator, in which every mint, version publication, credential grant, and status change is recorded.
- **Anchor** — a commitment of a registry-ledger Merkle root into a public blockchain transaction.
- **Tombstone** — the terminal public representation of a deactivated subject. A tombstoned record remains resolvable forever; it is never deleted (§7.2).
- **Registry operator** — the party operating the authoritative registry and its resolution surface; currently UUAID (uuaid.org), with the UUAID Foundation nonprofit incorporation in progress (§7.5).

### 2.3 Conformance classes

This Standard defines three normative conformance classes and one informative class.

#### 2.3.1 UUAID Resolver (normative)

A service that serves resolution for UUAID identifiers. A conforming UUAID Resolver:

1. MUST implement the IAASO resolution endpoint (§3.3) for both identifier profiles.
2. MUST implement the compact resolution endpoint (§3.2) for Profile A identifiers.
3. MUST implement the status endpoint and status-history endpoint (§4).
4. MUST serve responses as JSON (`application/json`).
5. MUST serve tombstoned records per §3.3 and §7.2 — a conforming resolver MUST NOT respond to a tombstoned identifier as if it were unknown.
6. MUST be publicly accessible without authentication for all endpoints defined in §3, §4, §5.2, §5.3, and §6.2.

#### 2.3.2 Verification Endpoint (normative)

A service that performs credential verification. A conforming Verification Endpoint:

1. MUST implement the credential verification endpoint (§5.1), executing all five itemized checks and reporting each check individually.
2. MUST implement the trust-list endpoint (§5.2).
3. MUST implement the cryptographic inventory endpoint (§5.3).

#### 2.3.3 Anchored Ledger (normative)

The integrity substrate behind a UUAID Resolver. A conforming Anchored Ledger:

1. MUST maintain an append-only, hash-chained event log using SHA-256 over payloads canonicalized with JCS [RFC 8785] (§6.1).
2. MUST anchor Merkle roots over batches of ledger events into a public blockchain (§6.3); the production anchoring chain is Polygon mainnet, CAIP-2 chain id `eip155:137`.
3. MUST serve Merkle inclusion receipts (§6.2) sufficient for the offline verification procedure of §6.4.

#### 2.3.4 Mirror Resolver (informative)

A read-only replica of a UUAID Resolver operated by a party other than the registry operator. No conformance requirements are defined for Mirror Resolvers in this version; see Annex A.1. This class is reserved so that future versions of this Standard can define it without renumbering.

### 2.4 Reference deployment

The reference deployment against which this Standard is written:

- Machine resolution and verification: `https://api.uuaid.org`
- Human-facing registry: `https://registry.uuaid.org`
- IAASO governance authority: `https://authority.iaaso.org`

All endpoint paths in this Standard are relative to the resolver base URL (`https://api.uuaid.org` in the reference deployment).

---

## 3. Resolution Protocol (Normative)

### 3.1 General requirements

1. All resolution endpoints defined in this section MUST be served over HTTPS.
2. All response bodies MUST be JSON.
3. Resolution endpoints MUST NOT require authentication.
4. Resolvers MUST accept UUID segments case-insensitively and MUST treat the lowercase form as canonical, per IAASO-1001.
5. Syntactic validation of the supplied identifier is governed by IAASO-1001; this Standard specifies only the resolver's observable responses.

### 3.2 Compact resolution endpoint

```
GET /resolve/:uuaid
```

Resolves a **Profile A (compact)** identifier.

**Responses:**

| Condition | HTTP status | Body |
|---|---|---|
| Compact identifier, subject found | `200` | Compact resolution object (below) |
| Syntactically invalid identifier | `400` | Error object |
| Compact identifier, subject unknown | `404` | Error object |
| Non-compact (Profile B) identifier | `404` | Error object indicating an unresolved type |

Profile B identifiers are **not** resolvable at this endpoint; clients holding a Profile B identifier MUST use the IAASO resolution endpoint (§3.3). The compact endpoint's `404` for a Profile B identifier does not assert that the subject is unknown.

**Compact resolution object (200):** the response MUST include:

- `uuaid` — the canonical identifier resolved.
- `type` — the object type.

For **agent** subjects, the response MUST additionally include:

- `agent` — an object including at least `uuid`, `uuaid`, `displayName`, `description`, `controller`, `partnerId`, and `status`.
- `profile` — the subject's public profile record (`null` when no profile has been published).
- `versions` — an array of immutable version records, each including at least `uuaid`, `manifestHash`, and `createdAt`.
- `credentials` — an array of credentials asserted about the subject.

For other object types, the response carries the members specific to that type alongside `uuaid` and `type` (e.g., a `version` member for `agent-version` subjects); clients MUST NOT assume the agent-specific members above are present for non-agent subjects.

Additional members MAY be present; clients MUST ignore members they do not recognize.

### 3.3 IAASO resolution endpoint

```
GET /iaaso/v1/resolve/:uuaid
```

Resolves identifiers of **both profiles**. This is the profile-complete resolution endpoint; Profile B (federated) identifiers resolve only here.

**Response:** a JSON resolution result:

| Member | Requirement | Description |
|---|---|---|
| `id` | REQUIRED | The canonical UUAID identifier resolved. |
| `subjectClass` | REQUIRED | The subject class of the identifier. |
| `resolutionStatus` | REQUIRED | Exactly one of the three values in §3.3.1. |
| `document` | CONDITIONAL | The `IAASOSubjectDocument` (§3.4). MUST be present when `resolutionStatus` is `found`; MUST be absent when `resolutionStatus` is `not-found`. |
| `statusRef` | REQUIRED | Reference to the subject's status endpoint (§3.5). |

Clients MUST dispatch on the `resolutionStatus` member and MUST NOT rely on the HTTP status code alone to distinguish resolution outcomes at this endpoint.

#### 3.3.1 Resolution status values

The `resolutionStatus` member MUST take exactly one of the following values:

| Value | Meaning |
|---|---|
| `found` | The identifier denotes a known subject; the subject document is included. Lifecycle status (active, suspended, etc.) is carried by the document's `status` member (§3.4) and by the status endpoint (§4.1), not by `resolutionStatus`. |
| `not-found` | The identifier is well-formed but denotes no subject known to this resolver. |
| `tombstoned` | The identifier denotes a subject that has been deactivated. The record persists (§7.2); the identifier is never reassigned. |

Resolvers MUST NOT define additional `resolutionStatus` values in v1 of this protocol. A resolver MUST return `tombstoned` — not `not-found` — for a deactivated subject; conflating the two is a conformance failure.

### 3.4 IAASOSubjectDocument (schemaVersion 1.1)

The subject document returned by §3.3 MUST carry `schemaVersion` `"1.1"` and MUST include the following members:

| Member | Description |
|---|---|
| `id` | The subject's canonical UUAID identifier. |
| `type` | Document type discriminator. |
| `issuedAt` | Timestamp at which this document instance was produced by the resolver. |
| `subjectClass` | The subject class. |
| `displayName` | Human-readable name of the subject. |
| `createdAt` | Timestamp of subject creation (mint). |
| `updatedAt` | Timestamp of the most recent update to the subject record. |
| `status` | Current lifecycle status of the subject. |
| `namespace` | The namespace under which the subject was minted. |
| `controller` | OPTIONAL — the controlling party, when registered. |
| `statusEndpoint` | The URL of the subject's status endpoint (§4.1). |
| `credentials` | Array of credentials asserted about the subject. |

`controller` is the only OPTIONAL member above; all others MUST be present. Producers MAY include additional members; consumers MUST ignore unrecognized members.

### 3.5 statusRef linkage

The `statusRef` member of the resolution result and the `statusEndpoint` member of the subject document link resolution to the status surface of §4. A resolver MUST populate these such that dereferencing them yields the subject's `IAASOStatusObject`. Clients requiring current lifecycle status (e.g., before relying on a credential) SHOULD dereference the status endpoint rather than caching the `status` member of a previously fetched subject document.

### 3.6 Human-facing registry and badges (informative)

The reference deployment additionally serves:

- a human-readable registry at `https://registry.uuaid.org`, with compact-profile paths of the form `/uuaid/<namespace>/<object-type>/<uuid>`;
- status badges at `GET /badge/agent/:uuaid.svg` and `GET /badge/credential/:id.svg`.

These surfaces are conveniences. They are **not authoritative**: relying parties MUST use the JSON endpoints of §3–§6, not badge images or HTML pages, as the basis for trust decisions.

---

## 4. Status and Status History (Normative)

### 4.1 Status endpoint — IAASOStatusObject (schemaVersion 1.1)

```
GET /iaaso/v1/status/:uuaid
```

Returns the subject's current lifecycle status as an `IAASOStatusObject` with `schemaVersion` `"1.1"`. The object MUST include:

| Member | Description |
|---|---|
| `id` | Identifier of this status object. |
| `type` | Object type discriminator. |
| `schemaVersion` | `"1.1"`. |
| `issuedAt` | Timestamp at which this status object was produced. |
| `subjectRef` | The UUAID identifier of the subject this status describes. |
| `status` | The subject's current lifecycle status. |
| `statusReasonCode` | Machine-readable reason code for the current status. |
| `effectiveAt` | Timestamp from which the current status is effective. |

### 4.2 Status history endpoint — ledger slice

```
GET /iaaso/v1/status/:uuaid/history
```

Returns the subject's status history as a **slice of the registry ledger** restricted to events concerning the subject. The response MUST include:

| Member | Description |
|---|---|
| `subjectRef` | The subject's UUAID identifier. |
| `count` | The number of events returned. |
| `events` | Array of ledger events, each including `seq` (global ledger sequence number), `at` (timestamp), `eventType`, `actor`, and `ledgerHash` (the event's hash in the hash chain, §6.1). |

### 4.3 Append-only semantics

1. The status history MUST be append-only. Events, once recorded, MUST NOT be modified, reordered, or removed from the history.
2. A status change (including deactivation/tombstoning) MUST be represented by **appending** a new event, never by rewriting prior events.
3. Each event's `seq` is its position in the global registry ledger, and its `ledgerHash` is its hash-chain value (§6.1). This gives every history entry a stable coordinate against which a Merkle inclusion receipt (§6.2) can be requested, tying the subject's visible history to the anchored ledger.

---

## 5. Verification (Normative)

### 5.1 Credential verification endpoint

```
POST /iaaso/v1/verify/credential
Content-Type: application/json

{ "credential_id": "<credential identifier>" }
```

A Verification Endpoint MUST execute the following **five itemized checks**, in the sense defined below, and MUST report each check individually in the response. The check identifiers are normative.

| Check id | Meaning |
|---|---|
| `schema-shape` | The credential record is well-formed: it conforms to the expected credential schema (required fields present, types correct). |
| `issuer-known` | The credential's issuer appears on the accredited issuer trust list (§5.2). A credential from an unknown or non-accredited issuer fails this check. |
| `signature-valid` | The credential's Ed25519 signature verifies against the issuer's registered public key over the issuer's canonical payload. |
| `status-active` | The credential's current status is active — it has not been revoked or suspended, and its subject has not been tombstoned in a way that invalidates it. |
| `interval-valid` | The credential's validity interval covers the time of verification (not yet valid → fail; expired → fail). |

**Response:** a JSON object that MUST include:

| Member | Description |
|---|---|
| `credential_id` | The credential identifier verified. |
| `agent_uuaid` | The UUAID identifier of the credential's subject. |
| `verified` | Boolean overall verdict. `verified` MUST be `true` only if **all five** checks pass. |
| `checks` | Array of per-check results, one entry per check id above, each reporting whether that check passed. |

A Verification Endpoint MUST NOT report `verified: true` while any individual check reports failure. Relying parties SHOULD inspect the itemized `checks` array — not only the aggregate `verified` flag — when diagnosing failures or applying policies stricter than this Standard.

### 5.2 Trust list endpoint

```
GET /iaaso/v1/trust/issuers
```

Returns the list of accredited credential issuers. The list is sourced from the IAASO governance authority (`authority.iaaso.org`); when the authority is not consulted, the resolver serves a static founding entry for **AIAU (AI Agent University)**, the founding accredited certification examiner.

Requirements:

1. The trust list MUST be publicly readable without authentication.
2. The `issuer-known` check (§5.1) MUST be evaluated against this list.
3. Additions to and removals from the trust list are governance actions of IAASO and are out of scope for this Standard; the resolver MUST reflect the authority's current list when the authority is available.

### 5.3 Cryptographic inventory endpoint

```
GET /iaaso/v1/crypto-inventory
```

Publishes the machine-readable inventory of cryptographic mechanisms in force, enabling relying parties to prepare for algorithm transitions (crypto-agility). The response MUST include:

- `suites` — the signature suites and their status. In v1:
  - `{ "alg": "ed25519", "status": "active" }` — the active signature algorithm.
  - `{ "alg": "ml-dsa-65", "status": "reserved", "transitionClass": "pqcPreferred" }` — reserved for post-quantum hybrid transition.
  - `{ "alg": "slh-dsa-128s", "status": "reserved" }` — reserved for post-quantum hybrid transition.
- `canonicalization` — `"JCS-RFC8785"`.
- `hashes` — `["sha256", "keccak256"]`. SHA-256 is used for the ledger hash chain (§6.1); Keccak-256 for the anchored Merkle tree (§6.2).

Signature envelopes in the registry ledger carry an open `alg` field; the reserved suites above are declared so that verifiers can implement them ahead of activation. Verifiers SHOULD reject envelopes whose `alg` is not listed as `active` in the inventory at the time of verification, unless operating under an explicit local policy to the contrary.

---

## 6. Integrity and Independent Verification (Normative)

### 6.1 Hash-chained ledger

The registry ledger underlying the resolution surface:

1. MUST be append-only.
2. MUST canonicalize event payloads using the JSON Canonicalization Scheme (JCS) [RFC 8785] before hashing.
3. MUST chain events by SHA-256, such that each event's `ledgerHash` commits to its canonicalized payload and its predecessor, making any retroactive modification of a recorded event detectable.
4. MUST record every subject mint, version publication, credential grant, and status change as a ledger event.
5. MUST use crypto-agile signature envelopes: the envelope's `alg` field is open, with `ed25519` active and `ml-dsa-65` / `slh-dsa-128s` reserved (§5.3).

### 6.2 Merkle inclusion receipts

```
GET /iaaso/v1/receipts/:seq
```

Returns a Merkle inclusion receipt proving that the ledger event with global sequence number `seq` is included under an on-chain anchor root. The receipt MUST include:

| Member | Description |
|---|---|
| `seq` | The global ledger sequence number of the event. |
| `leaf` | The leaf hash committing to the event; equal to the event's `ledgerHash` (§4.2, §6.1). |
| `index` | The leaf's position within the anchored Merkle tree (informational; sibling ordering along the proof path is carried explicitly by `proof`). |
| `proof` | The ordered array of proof steps from the leaf to the root. Each step is an object with two members: `hash` — the sibling hash at that level — and `position` — `"left"` or `"right"`, the side on which that sibling hash is concatenated relative to the running hash (§6.4 step 3). |
| `root` | The Merkle root under which the leaf is included. |
| `anchor` | The anchor record, including at least `txHash` (the anchoring transaction hash), `network` (the CAIP-2 chain identifier), and `eventCount` (the number of ledger events covered by this anchor). |

A receipt MUST contain sufficient information for a third party to recompute `root` from `leaf` and `proof` alone, without any additional data from the resolver, using the tree hash defined below.

**Tree construction.** The anchored Merkle tree takes as its leaves the `ledgerHash` values of ledger events `1..anchor.eventCount`, ordered by `seq` ascending; the receipt's `leaf` is therefore the event's `ledgerHash`. The pair hash is **Keccak-256** over the byte concatenation of the two child nodes (`keccak256(left ‖ right)`); an unpaired node at the end of a level is paired with a copy of itself. The tree hash (Keccak-256) is deliberately distinct from the SHA-256 used for the ledger hash chain (§6.1); both appear in the cryptographic inventory (§5.3).

### 6.3 On-chain anchoring

1. Merkle roots over ledger events MUST be anchored in transactions on a public blockchain. The production anchoring network is **Polygon mainnet**, CAIP-2 chain identifier **`eip155:137`**.
2. The `anchor.network` member of a receipt MUST identify the anchoring chain by its CAIP-2 identifier.
3. Anchoring is batched: one anchor covers `eventCount` ledger events under a single root. Anchoring cadence is an operational matter and is not constrained by this Standard.

### 6.4 Offline verification procedure

This procedure allows a third party to verify that a ledger event — for example, an event appearing in a subject's status history (§4.2) — is committed under a public on-chain anchor, **without trusting the resolver**. After step 1, the procedure requires no further interaction with the resolver; its trust base reduces to the hash functions of §6.1–§6.2 (SHA-256 for the event hash chain; Keccak-256 for the Merkle tree) and the consensus of the anchoring chain.

**Inputs:** a receipt (obtained from `GET /iaaso/v1/receipts/:seq`, or from any cache or archive of previously fetched receipts), and independent read access to the anchoring chain (any Polygon mainnet node, self-hosted or third-party, of the verifier's own choosing).

**Procedure:**

1. **Obtain the receipt.** Fetch `GET /iaaso/v1/receipts/:seq` for the event's sequence number, or load a previously archived receipt. (This is the only step that may involve the resolver.)
2. **Bind the receipt to the event of interest.** Confirm that the receipt's `seq` matches the event's `seq` and that the receipt's `leaf` equals the event's ledger hash — for a status-history event, the `ledgerHash` reported in that event (§4.2). A verifier holding the event's full canonical payload SHOULD additionally recompute the event hash per §6.1 (JCS canonicalization, SHA-256) and confirm it matches, rather than trusting the reported hash.
3. **Recompute the Merkle root.** Starting from `leaf`, iterate over `proof` in order: at each step, concatenate the step's sibling `hash` with the running hash on the side indicated by the step's `position` member (`"left"` → sibling ‖ running; `"right"` → running ‖ sibling) and hash the concatenation with **Keccak-256** (§6.2). The final value MUST equal the receipt's `root`. If it does not, the receipt is invalid: **stop; verification fails.**
4. **Fetch the anchor transaction independently.** Query the anchoring chain identified by `anchor.network` (`eip155:137`) for the transaction `anchor.txHash`, using an independent node or explorer **not** operated by the resolver.
5. **Extract and compare the anchored root.** Extract the Merkle root committed in that transaction and confirm it equals the receipt's `root`. If it does not, the receipt is not covered by that anchor: **verification fails.**
6. **Confirm anchor finality.** Confirm the anchoring transaction is confirmed on `eip155:137` to the verifier's own finality/confirmation-depth policy.

**Outcome.** If all steps succeed, the verifier has established — with no trust in the resolver beyond step 1's data transport — that the ledger event existed and was committed, in its recorded form and position, no later than the time of the on-chain anchor. Any subsequent tampering with that event by the registry operator would be detectable, because the tampered event could not produce the anchored root.

**What this does and does not prove.** Inclusion receipts prove *inclusion and immutability* of anchored events. They do not, by themselves, prove *completeness* (that the resolver has shown the verifier every event for a subject) or *freshness* (that no newer events exist). Verifiers with completeness or freshness requirements SHOULD compare consecutive `seq` values in a subject's history for gaps, SHOULD note `anchor.eventCount` across receipts, and MAY archive receipts over time to detect equivocation. See also §8.

---

## 7. Persistence Commitments (Normative)

This section states the persistence guarantees of the UUAID identifier system, in the tradition of persistent-identifier schemes (DOI, ARK). Each commitment is stated together with the mechanism that enforces or evidences it.

### 7.1 Identifiers are minted once and never reissued

1. A UUAID identifier, once minted, MUST NOT be reissued, reassigned, or recycled to a different subject — ever, including after tombstoning.
2. Every mint MUST be recorded in the registry ledger (§6.1), giving each identifier a permanent, anchorable birth record.
3. The identifier itself MUST NOT change over the subject's lifetime. All evolution of the subject is expressed through append-only mechanisms: immutable, content-hashed version manifests (each version record carries a `manifestHash`), credential grants, and status events. Updating a subject never alters its identifier or rewrites its history.

### 7.2 Records are never deleted — tombstone semantics

1. Registry records MUST NOT be deleted. Deactivation of a subject MUST be expressed as a **tombstone**: the resolver thereafter reports `resolutionStatus: "tombstoned"` (§3.3.1) for the identifier.
2. A tombstoned identifier MUST remain resolvable indefinitely. Tombstoning changes what the resolver asserts about the subject's status; it does not remove the record, the identifier, or the history.
3. Because identifiers are never reissued (§7.1), a reference to a tombstoned identifier remains permanently unambiguous.

### 7.3 Status history is append-only and anchored

1. The status history of every subject MUST be append-only (§4.3).
2. Because history events are ledger events, they participate in the hash chain (§6.1) and are covered by on-chain anchors (§6.3), making retroactive falsification of a subject's history detectable by any third party via §6.4.

### 7.4 Resolver operator commitments

The registry operator, in operating the reference deployment, commits to:

1. serving the resolution, status, verification, trust-list, crypto-inventory, and receipt endpoints of §3–§6 publicly and without authentication;
2. preserving tombstone semantics (§7.2) and never deleting records;
3. never reissuing identifiers (§7.1);
4. recording all registry mutations in the anchored ledger and continuing to publish anchors to `eip155:137`;
5. publishing this protocol and the identifier grammar as open specifications (reference: `https://github.com/uuaid/spec`), so that the resolution surface is independently reimplementable.

### 7.5 Operator continuity and cessation

The registry is operated by UUAID (uuaid.org). Incorporation of the **UUAID Foundation**, a nonprofit intended to hold the operator commitments above under a public charter (uuaid.foundation), is in progress.

Should the registry operator cease operation, the following holds. This subsection is deliberately candid about what is and is not guaranteed **today**:

**Guaranteed by construction (survives operator cessation):**

1. **On-chain anchors persist.** Anchor roots already committed to Polygon mainnet (`eip155:137`) exist independently of the operator and remain publicly readable for as long as that chain persists.
2. **Archived data remains verifiable.** Any party holding previously fetched subject documents, status histories, ledger events, and inclusion receipts can continue to verify their integrity against the on-chain anchors using §6.4, with no participation from the operator.
3. **The protocol is reimplementable.** This Standard, IAASO-1001, and the open specification repository are sufficient for an independent party to stand up a conforming resolver over any authentic copy of the ledger data, and for relying parties to verify that such a resolver's data matches the anchored roots.

**Not guaranteed today (stated honestly):**

4. **Continuous resolution availability** after operator cessation is not cryptographically guaranteed: there is, at present, a single authoritative resolver and no operational independent mirror. Anchors prove integrity of data one holds; they do not by themselves keep an online service running.
5. **A complete public replica of the full ledger** is not yet continuously distributed to independent parties. Reconstruction after cessation therefore depends on the ledger data being handed over, escrowed, or archived. Mirror/federated resolvers and formal succession arrangements are the subject of Annex A.1 and of the UUAID Foundation charter work.

In summary: **integrity and verifiability of everything already anchored survive the operator; availability of live resolution does not yet.** Closing that gap is the primary persistence objective of future versions of this Standard.

---

## 8. Security Considerations

1. **Transport security.** All endpoints are served over HTTPS. Clients MUST NOT accept resolution or verification responses over plaintext transport.
2. **Resolver trust and its limits.** For ordinary resolution, the client trusts the resolver for freshness and completeness. The anchored-ledger mechanisms (§6) bound this trust: any recorded event's existence and content can be verified independently (§6.4). Clients with adversarial-resolver threat models SHOULD archive receipts and monitor for equivocation (two inconsistent histories for the same subject cannot both verify against the same anchored roots once their events are anchored).
3. **Freshness and revocation latency.** A subject document or credential-verification result reflects the resolver's state at `issuedAt`. Relying parties making consequential decisions SHOULD re-check `status-active` (via §5.1 or §4.1) at decision time rather than relying on cached verdicts; tombstoning or revocation after caching is otherwise invisible.
4. **Signature verification.** `signature-valid` (§5.1) is evaluated by the Verification Endpoint. Relying parties that must not trust the endpoint MAY independently verify Ed25519 signatures using issuer keys from the trust list and payload canonicalization per §5.3; nothing in this protocol prevents client-side re-verification.
5. **Trust-list integrity.** The `issuer-known` check is only as strong as the trust list (§5.2). The list is governed by IAASO via `authority.iaaso.org`; compromise of the governance authority is a systemic risk and is addressed by IAASO governance procedures outside this Standard.
6. **Cryptographic agility and PQC.** Ed25519 is the active suite; ML-DSA-65 and SLH-DSA-128s are reserved for post-quantum transition (§5.3). Verifiers SHOULD consult the crypto inventory rather than hard-coding algorithm assumptions, so that suite activation does not break them.
7. **Anchoring-chain assumptions.** The offline verification procedure (§6.4) reduces trust to the hash functions of §6.1–§6.2 and the consensus/persistence of `eip155:137`. A deep reorganization or failure of the anchoring chain would weaken anchor guarantees for recent anchors; verifiers with high-assurance requirements SHOULD apply conservative confirmation depths (§6.4 step 6).
8. **Denial of service.** Public unauthenticated endpoints are exposed to volumetric abuse. Operators MAY apply rate limiting, provided it does not discriminate in a way that undermines the public-verifiability commitments of §7.4.
9. **Badges are not evidence.** Badge SVGs (§3.6) are unauthenticated conveniences and MUST NOT be used as verification inputs.

---

## 9. Privacy Considerations

1. **Public-by-design registry.** The UUAID registry is a *public* registry: subject documents, display names, descriptions, controllers, credentials, status, and status history are published deliberately, without authentication, to anyone. Registration constitutes publication.
2. **Registrant awareness.** Parties minting identifiers (partners and self-serve registrants) do so understanding that submitted fields (`displayName`, `description`, `controller`, credential contents, etc.) become world-readable. Registrants SHOULD NOT place personal data, secrets, or sensitive information in registry fields beyond what they intend to publish permanently.
3. **Permanence versus erasure.** The persistence commitments of §7 are in direct, intentional tension with data-erasure expectations: records are never deleted, history is append-only, and anchored hashes are immutable. Tombstoning marks a subject inactive but does not remove previously published data, and anchored commitments cannot be retracted. Registrants and operators should treat every write to the registry as permanent publication.
4. **What anchors reveal.** On-chain anchors commit only Merkle roots (hashes); they place no registry payload data on-chain. Payload confidentiality is therefore unaffected by anchoring — but the registry payloads themselves are public regardless (item 1).
5. **Query privacy.** Resolution queries reveal to the resolver which identifiers a client is interested in. Clients with query-privacy requirements may fetch over privacy-preserving transports; the protocol imposes no client identification.
6. **Human subjects.** Where a subject record concerns or names a human (e.g., a controller), the registrant is responsible for having the right to publish that information under applicable law. The protocol provides tombstoning as the strongest available remediation; it does not provide erasure.

---

## 10. Annex A — Future Work (Informative)

This annex is **informative**. Nothing in it is implemented as specified here, and nothing in it creates conformance requirements. Items are listed to signal direction and to reserve design space for future versions of this Standard.

**A.1 Mirror and federated resolvers.** Definition of the Mirror Resolver conformance class (§2.3.4): read-only replicas operated by independent parties, with continuous ledger replication, cross-resolver consistency proofs against the shared anchor roots, and a discovery mechanism. This is the intended remedy for the availability gap described in §7.5.

**A.2 Meta-resolver registrations.** Registration of the `uuaid` scheme/prefix with global meta-resolvers such as identifiers.org and N2T (n2t.net), so that generic persistent-identifier tooling can resolve UUAID identifiers without UUAID-specific configuration.

**A.3 `?info` inflections.** ARK-style inflections on resolution URLs (e.g., appending `?info`) returning machine- and human-readable metadata about the identifier and its persistence policies, as distinct from the subject document itself.

**A.4 Hosted DID document endpoint.** A dedicated endpoint (e.g., `GET /1.0/identifiers/<did>`) serving W3C DID documents for `did:uuaid`, suitable for a Universal Resolver driver. DID documents constructed under `did:uuaid` may omit `verificationMethod` when the subject has no registered public key; service endpoints and controller are always constructible from the resolution surface defined in this Standard.

**A.5 Namespace delegation (Profile B institutional minting).** Operational delegation of Profile B `<jurisdiction>:<namespace>` prefixes to accredited institutions (registry nodes, education providers, governance bodies), enabling federated minting under delegated authority while preserving global resolvability through the IAASO resolution endpoint and global integrity through the anchored ledger.

**A.6 Receipt and ledger archival program.** A publicly downloadable, continuously updated archive of ledger events and receipts, enabling any party to maintain a full offline-verifiable copy of the registry (strengthening §7.5 items 4–5).

---

## 11. Document Metadata

```yaml
code: IAASO-0002
title: Public Resolution and Verification Protocol
version: "1.0"
stage: proposed
committee: standards-council
doc_url: "TBD — to be assigned upon ratification (placeholder)"
supersedes: none
language: en
date: 2026-07-06
registry_operator: UUAID (uuaid.org); UUAID Foundation (nonprofit incorporation in progress; charter: https://uuaid.foundation)
standards_body: IAASO — International Autonomous Agents Standards Organization (https://iaaso.org)
contact:
  organization: UUAID Foundation (incorporation in progress)
  email: madanksamy@gmail.com
  website: https://uuaid.org
reference_deployment:
  resolver: https://api.uuaid.org
  human_registry: https://registry.uuaid.org
  governance_authority: https://authority.iaaso.org
open_spec_repo: https://github.com/uuaid/spec
```

### References

**Normative:**

- [RFC 2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119.
- [RFC 8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174.
- [RFC 8785] Rundgren, A., Jordan, B., Erdtman, S., "JSON Canonicalization Scheme (JCS)", RFC 8785.
- [RFC 8032] Josefsson, S., Liusvaara, I., "Edwards-Curve Digital Signature Algorithm (EdDSA)", RFC 8032. (Ed25519)
- IAASO-1001, "Autonomous Agent Identifier Standard" (draft, tc-1) — normative identifier grammar.
- IAASO-0001, "Universal Agent Protocol (UAP) v1" (ratified, standards-council) — https://github.com/uuaid/spec
- CAIP-2, "Blockchain ID Specification" (Chain Agnostic Improvement Proposals) — chain identifier `eip155:137`.

**Informative:**

- [RFC 9562] Davis, K., Peabody, B., Leach, P., "Universally Unique IDentifiers (UUIDs)", RFC 9562. (UUIDv7)
- IAASO-1101, "Trust Profile Object Standard" (draft).
- IAASO-1201, "Security and Runtime Governance Standard" (draft).
- ADR-001, UUAID dual identifier profiles (Profile A compact / Profile B federated).
- NIST FIPS 204, "Module-Lattice-Based Digital Signature Standard" (ML-DSA).
- NIST FIPS 205, "Stateless Hash-Based Digital Signature Standard" (SLH-DSA).
- ARK Alliance, "The ARK Identifier Scheme" — persistence and inflection precedent.
- International DOI Foundation, "DOI Handbook" — persistence-policy precedent.

---

*End of IAASO-0002 v1.0 (proposed).*
