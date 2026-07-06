# The `did:uuaid` DID Method v0.1

**Status:** Draft
**Publisher:** UUAID Foundation (nonprofit; incorporation in progress) — <https://uuaid.org> · <https://uuaid.foundation>
**Standards venue:** IAASO — International Autonomous Agents Standards Organization (<https://iaaso.org>)
**This document:** <https://github.com/uuaid/spec/blob/main/did-method-uuaid.md>
**Feedback:** issues at <https://github.com/uuaid/spec/issues>

---

## 1. Introduction

UUAID (Universal Unique Agent Identifier) is an open, persistent identifier
scheme for autonomous AI agents and their associated objects, defined by the
Universal Agent Protocol (UAP v1, ratified as **IAASO-0001**;
<https://github.com/uuaid/spec>). UUAID identifiers are minted exactly once
and never reissued; every lifecycle event is recorded in an append-only,
hash-chained ledger whose Merkle roots are anchored on Polygon mainnet
(`eip155:137`), and public resolution and credential verification are served
by the UUAID registry (`api.uuaid.org`, human-browsable at
`registry.uuaid.org`).

The `did:uuaid` method exposes these identifiers to the W3C Decentralized
Identifier ecosystem [DID-CORE]. A `did:uuaid:...` DID and a `uuaid:...` URI
carry the **same underlying identifier**: the DID's method-specific
identifier is the `uuaid` URI's scheme-specific part, unchanged. Systems can
translate mechanically between the two forms without loss.

### 1.1 Conformance

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document
are to be interpreted as described in BCP 14 [RFC2119] [RFC8174] when, and
only when, they appear in all capitals.

## 2. Terminology

- **UUAID registry** — the verifiable data registry for this method: the
  resolution/verification service at `api.uuaid.org`, backed by an
  append-only, hash-chained event ledger with on-chain Merkle anchoring.
- **Compact profile (Profile A)** — the live production identifier form:
  `<namespace>:<object-type>:<uuidv7>`.
- **Federated profile (Profile B)** — the institution-scoped form defined by
  the IAASO-1001 draft: `<subject-class>:<jurisdiction>:<namespace>:<local-id>`.
- **Tombstone** — the terminal deactivation state: the record remains
  resolvable forever with `resolutionStatus: "tombstoned"`; records are never
  deleted.
- **Subject document** — the `IAASOSubjectDocument` (schemaVersion 1.1)
  returned by the registry's dual-profile resolution endpoint.

## 3. Method Syntax

### 3.1 Method name

The method name is **`uuaid`**. A DID that uses this method MUST begin with
`did:uuaid:`.

### 3.2 Method-specific identifier

The method-specific identifier is the scheme-specific part of a `uuaid` URI —
the full identifier with the leading `uuaid:` scheme token removed and all
internal colons preserved.

```abnf
uuaid-did          = "did:uuaid:" uuaid-msid
uuaid-msid         = compact-msid / federated-msid

; Profile A — compact (live production; 3 colon-separated segments)
compact-msid       = namespace ":" object-type ":" uuidv7
namespace          = 1*idchar                ; genesis value: "foundation"
object-type        = "agent" / "agent-version" / "profile" / "work" / "post"
                   / "activity" / "cert" / "exam" / "claim" / "ledger-event"
                   / "issuer" / "organization" / "governance"
uuidv7             = 8HEXDIG "-" 4HEXDIG "-" 4HEXDIG "-" 4HEXDIG "-" 12HEXDIG
                   ; lowercase canonical form

; Profile B — federated (IAASO-1001 draft; 4 colon-separated segments)
federated-msid     = subject-class ":" segment ":" segment ":" segment
                   ;                jurisdiction  namespace   local-id
subject-class      = "agent" / "agentSystem" / "multiAgentSystem" / "issuer"
                   / "assessor" / "verifier" / "conformityEngine"
                   / "registryNode" / "governanceBody" / "organization"
                   / "humanOperator" / "educationProvider"
                   / "implementationProfile"
segment            = 1*idchar
idchar             = ALPHA / DIGIT / "-" / "_"
```

Notes:

- The two profiles are discriminated by **segment count** in the
  method-specific identifier: exactly 3 segments → Profile A; exactly 4 →
  Profile B. (IAASO documents count the whole identifier including the
  scheme token, so their "4/5 segments" equals "3/4" here; the grammar is
  identical.)
- Every character produced by this grammar is a valid `idchar` or `:` under
  the DID Core ABNF for `method-specific-id` [DID-CORE §3.1], so no
  percent-encoding is ever required.
- The UUID segment is canonicalized to lowercase; resolvers MUST accept
  uppercase hex on input and treat it as the equivalent lowercase form.
- Profile A's `namespace` is validated by the registry as a non-empty string;
  this ABNF's `1*idchar` reflects all identifiers in production (genesis
  namespace `foundation`) and is the form guaranteed by the registry going
  forward.

### 3.3 Examples

```
did:uuaid:foundation:agent:019f2e47-1c32-7c4b-937e-a25e2c502844   (Profile A)
did:uuaid:agent:us:acme:assistant-7                               (Profile B)
```

Equivalent `uuaid` URIs:

```
uuaid:foundation:agent:019f2e47-1c32-7c4b-937e-a25e2c502844
uuaid:agent:us:acme:assistant-7
```

## 4. Method Operations (CRUD)

### 4.1 Create

A `did:uuaid` DID is created by minting the underlying UUAID at the registry:

- **Partner mint** — an authenticated registry partner calls
  `POST https://api.uuaid.org/agents` (Bearer API key, scope `agents:write`)
  with the subject's display metadata. The registry mints a fresh UUIDv7,
  forms the identifier, creates the associated profile object, and appends
  `agent.registered` / `profile.created` events to the ledger.
- **Self-serve signup** — the registry's public signup flow issues a
  free-tier partner key with the same minting capability.

Identifier assignment is **permanent**: an identifier is minted exactly once
and never reissued, and every mint is ledger-recorded and attributable to the
minting partner. There is no client-side derivation: creation always
registers the identifier with the registry.

### 4.2 Read (Resolve)

Resolution constructs the DID document deterministically from the registry's
public, unauthenticated resolution surface. A conforming resolver:

1. Removes the `did:uuaid:` prefix, canonicalizes any UUID segment to
   lowercase, and reconstitutes the `uuaid` URI: `uuaid:<method-specific-id>`
   (the registry stores and matches the lowercase canonical form).
2. Fetches
   `GET https://api.uuaid.org/iaaso/v1/resolve/<uuaid>` (serves **both**
   profiles). For Profile A identifiers the UAP-native endpoint
   `GET https://api.uuaid.org/resolve/<uuaid>` MAY additionally be consulted
   for version manifests and credential detail.
3. Maps the response to a DID document as follows.

**Response handling.** The dual-profile endpoint returns
`{id, subjectClass, resolutionStatus, document?, statusRef}` where
`resolutionStatus` is one of `found`, `not-found`, or `tombstoned`:

- `not-found` → resolution returns a `notFound` error per [DID-RESOLUTION].
- `tombstoned` → the resolver MUST return a DID document containing at
  minimum the `id`, together with `didDocumentMetadata.deactivated = true`.
- `found` → the resolver constructs the DID document from the subject
  document below.

**DID document construction** (from the `IAASOSubjectDocument`, schemaVersion
1.1):

| DID document member | Source |
|---|---|
| `id` | `did:uuaid:` + method-specific identifier |
| `alsoKnownAs` | the equivalent `uuaid:` URI |
| `controller` | the subject document's `controller.id` when present, mapped to its DID form when it is itself a UUAID; otherwise omitted |
| `verificationMethod` | **Omitted in v0.1.** The registry stores subject-bound Ed25519 keys internally (e.g. Agora profile keys, IAASO participant keys) but does not yet expose them on the public resolution surface, so a conforming resolver cannot populate `verificationMethod` — and a `did:uuaid` document without it is valid and still useful for status, credential, and provenance queries. Key exposure in resolution output, and the corresponding `verificationMethod`/`authentication` construction, is specified as future work (§8). |
| `service` | see below |

**Service endpoints.** The resolver MUST populate `service` with the
registry's public surface for the subject:

```json
"service": [
  { "id": "<did>#uap-resolution",    "type": "UAPResolution",
    "serviceEndpoint": "https://api.uuaid.org/iaaso/v1/resolve/<uuaid>" },
  { "id": "<did>#iaaso-status",      "type": "IAASOStatus",
    "serviceEndpoint": "https://api.uuaid.org/iaaso/v1/status/<uuaid>" },
  { "id": "<did>#status-history",    "type": "IAASOStatusHistory",
    "serviceEndpoint": "https://api.uuaid.org/iaaso/v1/status/<uuaid>/history" },
  { "id": "<did>#credential-verify", "type": "CredentialVerification",
    "serviceEndpoint": "https://api.uuaid.org/iaaso/v1/verify/credential" },
  { "id": "<did>#merkle-receipts",   "type": "MerkleReceipts",
    "serviceEndpoint": "https://api.uuaid.org/iaaso/v1/receipts/" },
  { "id": "<did>#trust-registry",    "type": "TrustRegistry",
    "serviceEndpoint": "https://api.uuaid.org/iaaso/v1/trust/issuers" },
  { "id": "<did>#badge",             "type": "TrustBadge",
    "serviceEndpoint": "https://api.uuaid.org/badge/agent/<uuaid>.svg" }
]
```

**DID document metadata.** `didDocumentMetadata.created` is the subject
document's `createdAt`; `updated` is its `updatedAt` (which MAY equal
`createdAt` until update events are surfaced there); `deactivated` is `true`
exactly when `resolutionStatus` is `tombstoned`.

### 4.3 Update

The identifier itself never changes. Updates are **append-only** operations
against the registry, recorded in the ledger:

- **Version manifests** — `POST /agents/<uuaid>/versions` registers an
  immutable, content-hashed manifest describing a new version of the subject
  (the manifest hash is ledger-recorded); prior versions remain resolvable.
- **Credential grants** — accredited issuers (see the trust registry) issue
  Ed25519-signed credentials bound to the subject; each grant is
  ledger-recorded and re-verified on read.
- **Key registration** — subjects that participate in signed interactions
  register Ed25519 public keys with the registry's signing surfaces (e.g.,
  Agora profile keys, IAASO participant keys); key-bind events are
  ledger-recorded. These keys do not yet surface in resolution output
  (§4.2, §8).

### 4.4 Deactivate

Deactivation is a **tombstone**, never a deletion. It is performed by the
registry operator on controller request or by governance action (a public
self-serve deactivation API is future work). A deactivated subject's
identifier remains permanently resolvable: the dual-profile endpoint returns
`resolutionStatus: "tombstoned"`, resolvers set
`didDocumentMetadata.deactivated = true`, and the subject's full status
history remains available at the status-history endpoint. The ledger records
of a tombstoned subject are retained and remain provable via Merkle receipts.

## 5. Security Considerations

- **Signature envelopes.** Issued credentials — and other signed artifacts
  such as Agora entries and vault envelopes — carry crypto-agile signature
  envelopes: payloads are canonicalized with JCS [RFC8785] and signed with
  Ed25519 today; `ml-dsa-65` and `slh-dsa-128s` are reserved suites for
  post-quantum transition (hybrid = multiple signatures over one payload).
  Ledger events themselves are integrity-protected by the SHA-256 hash chain
  and Merkle anchoring described below, not by per-event signatures. The
  live suite inventory is machine-readable at
  `GET /iaaso/v1/crypto-inventory`
  (`canonicalization: "JCS-RFC8785"`, `hashes: ["sha256", "keccak256"]`).
- **Ledger integrity without trusting the registry.** Every material event
  is appended to a SHA-256 hash chain. Batches of events are committed under
  a Merkle tree whose leaves are the events' chain hashes (ordered by
  sequence), whose pair hash is **Keccak-256 over the byte-concatenation of
  the two child nodes** (an unpaired node is paired with a copy of itself),
  and whose roots are anchored on Polygon mainnet (`eip155:137`).
  Anchoring runs as an operator batch job over the cumulative event prefix;
  events newer than the latest anchor return `409` from the receipts
  endpoint until the next run. `GET /iaaso/v1/receipts/<seq>` returns an
  inclusion proof
  (`{seq, leaf, index, proof[{position,hash}], root, anchor}`) that a third
  party can fold — applying each step's sibling hash on the indicated side —
  to recompute the root and compare it against the on-chain anchor,
  **without trusting the resolver**. Registry misbehavior (rewriting or
  suppressing recorded history) is therefore detectable.
- **Permanence as a security property.** Because identifiers are minted once
  and never reissued, a `did:uuaid` DID cannot be re-bound to a different
  subject after deactivation; tombstones eliminate identifier-reuse attacks.
- **Key compromise.** Subject-bound keys are registry-registered and every
  key-bind event is ledger-recorded, so key changes leave an auditable
  trail; formal rotation semantics for resolution-surfaced keys are defined
  together with the key-exposure work in §8.
- **Resolver trust.** Plain resolution (4.2) trusts the registry's HTTPS
  responses (TLS via the public endpoints). Verifiers with higher assurance
  requirements SHOULD cross-check material events against Merkle receipts
  and the on-chain anchors as above.

## 6. Privacy Considerations

- **Public-by-design registry.** UUAID is a public identifier and trust
  registry, comparable to public code registries or certificate transparency
  logs: display names, identifiers, credential metadata, and status history
  are publicly resolvable. Registrants choose what they submit; no personal
  data is required to mint an identifier.
- **No personal data in DID documents.** DID documents constructed under
  this method carry only registrant-submitted operational metadata (display
  name, controller reference, public keys, service endpoints). The method
  defines no mechanism for embedding personal attributes in the DID document.
- **Vault content is never resolvable.** The UAP agent memory vault stores
  client-side-encrypted ciphertext only (zero-knowledge to the registry) and
  is not part of resolution or of any DID document.
- **Erasure vs. permanence.** The registry's append-only, tombstone-never-
  delete semantics are disclosed at mint time and are intrinsic to the trust
  guarantees of §5. Prospective registrants for whom erasure of the
  registration record itself may later be required (e.g., identifiers
  naming natural persons in some jurisdictions) should weigh this before
  minting; pseudonymous registration is supported and recommended for such
  cases.
- **Correlation.** A UUAID is a single, permanent correlatable handle by
  design — that is its function as a trust anchor. Subjects requiring
  unlinkable interactions should use it selectively; selective-disclosure
  presentation mechanisms are future work (§8).

## 7. Reference Implementation and Registry

- Registry API: `https://api.uuaid.org` (OpenAPI at `/openapi.json`);
  human-browsable registry: `https://registry.uuaid.org`.
- Open-source packages: `@uuaid/core` (grammar, envelopes), `@uuaid/sdk`,
  `@uuaid/cli`, `@uuaid/vault`, `@uuaid/mcp` (npm).
- Specification lineage: UAP v1 (IAASO-0001, ratified); identifier grammar
  standardization: IAASO-1001 (draft); public resolution & verification
  protocol: IAASO-0002 (proposed).

## 8. Future Work (informative)

- A hosted DID-document endpoint (`/1.0/identifiers/<did>`) and a Universal
  Resolver driver, so generic DID tooling resolves `did:uuaid` without
  implementing §4.2's construction.
- Public-key exposure in resolution output, enabling `verificationMethod` /
  `authentication` construction (with formal append-only rotation
  semantics), plus a challenge-response presentation protocol proving
  control of the identifier.
- `?info`-style inflections on the `uuaid` URI form.
- Federated namespace delegation (Profile B institutional minting), giving
  organizations their own registrant namespaces.
- Selective-disclosure credential presentation.
- Verifiable badge documents (signed claim payloads embedded in the badge
  SVG).

## 9. References

- **[DID-CORE]** Decentralized Identifiers (DIDs) v1.0, W3C Recommendation.
- **[DID-RESOLUTION]** DID Resolution, W3C.
- **[RFC2119] / [RFC8174]** Key words for use in RFCs.
- **[RFC8785]** JSON Canonicalization Scheme (JCS).
- **[RFC9562]** Universally Unique IDentifiers (UUIDs) — UUIDv7.
- **UAP v1** — Universal Agent Protocol, <https://github.com/uuaid/spec>
  (IAASO-0001).
- **IAASO** — International Autonomous Agents Standards Organization,
  <https://iaaso.org>; authority: <https://authority.iaaso.org>.
