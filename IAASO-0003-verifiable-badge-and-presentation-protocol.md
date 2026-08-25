[← Index](README.md)

# IAASO-0003 — Verifiable Agent Badge & Presentation Protocol

- **Status:** Draft v1.1 (reference implementation shipped and deployed)
- **v1.1, 2026-08-25:** issuer pinning raised SHOULD → **MUST** (§4.3), the
  `L0-selfsigned` level added (§5), and §5.1 added for name claims. Reason: the
  reference implementation was shown to verify a self-minted forgery as
  `L1-signed`. The specification permitted that reading; both were wrong.
- **Series:** IAASO (International Autonomous Agents Standards Organization)
- **Depends on:** IAASO-0001 (UAP identifiers), IAASO-0002 (Public Resolution & Verification), ADR-002 (crypto-agility)
- **Reference implementation:** `@uuaid/core` (`badge.ts`), `apps/api` (`badge-verifiable.ts`), `uuaid verify-badge`, `verify-badge.html`

## 1. Abstract

A **Verifiable Agent Badge** is a portable, tamper-evident, cryptographically
signed *presentation* of a UUAID subject's identity and credentials, carried
inside an SVG so the same artifact is both human-visible (a shield) and
machine-verifiable (its proof lives in the SVG `<metadata>`). It is the "SSL
padlock" made detachable: an agent can carry it, embed it, or hand it over, and
any relying party can verify it — offline for tamper-evidence, online for
liveness.

The trust model is the **credential card / clearance badge**: an authority (the
UUAID registry) signs an attestation that a bearer carries. Presenting the badge
is not enough to *impersonate* the subject — a relying party may **challenge**
the presenter to prove possession of the subject's own key (§5), exactly as a
guard checks that the face matches the ID.

Badges are **quantum-ready by default** (§6): each is signed with a hybrid pair
of an Ed25519 (classical) and an ML-DSA-65 (post-quantum, FIPS 204) signature.

## 2. Motivation

IAASO-0002 gives a *live* verification surface (`/iaaso/v1/resolve`,
`/verify/credential`). But agents increasingly act across trust boundaries —
one organisation dispatches an agent to another's system — and the relying party
needs to decide *trust* at the moment of contact, often without a prearranged
integration. A signed, self-describing badge lets the receiving side answer
"who is this, who vouches for it, and is it really them?" from the artifact
itself, with a live cross-check available but not required for a first decision.

## 3. Terminology

| Term | Meaning |
|---|---|
| **Badge** | A `SignatureEnvelope<VerifiableBadgePayload>` (§4), usually delivered inside an SVG. |
| **Issuer / registry** | The authority that signs badges. Its public key(s) are published at a well-known URL (§4.3). |
| **Subject** | The UUAID the badge is about (an agent in v1). |
| **Presentation key** | The subject's own Ed25519 key (an Agora profile key), used for proof-of-possession (§5). |
| **Relying party (RP)** | Whoever verifies a badge or presentation. |
| **Bearer badge** | A badge with no subject presentation key — tamper-evident but copyable (L1 only). |

The key words MUST, SHOULD, MAY are per RFC 2119.

## 4. Badge format

A badge is a crypto-agile signature envelope (`@uuaid/core`): `{ payload,
payloadHash, signatures[] }`, where `payloadHash = "0x" + sha256(JCS(payload))`
(RFC 8785 canonicalization) and each signature is `{ alg, keyId, publicKey,
signature, created }` with `publicKey`/`signature` hex-encoded.

### 4.1 Payload (`VerifiableBadgePayload`)

| Field | Type | Notes |
|---|---|---|
| `@type` | const `"UUAIDVerifiableBadge"` | |
| `spec` | const `"IAASO-0003"` | |
| `v` | const `"1.0"` | |
| `subject.uuaid` | string | The subject UUAID (IAASO-0001, either profile). |
| `subject.displayName` | string? | |
| `subject.controller` | string? | Controller DID, when set. |
| `subject.presentationKey` | `{alg,publicKey,keyId}` \| `null` | `null` ⇒ bearer badge; else the subject's own key for §5. |
| `status` | string | IAASO status enum (IAASO-0002), computed at issue time. |
| `statusReasonCode` | string? | |
| `credentials[]` | `{id,certName?,certLevel?,status?,issuer,issuedAt?,expiresAt?,signingKeyId?}` | Snapshot of held credentials. |
| `issuer` | `{id,name,keyId}` | `keyId` identifies the registry key that signed. |
| `issuedAt` | ISO 8601 | |
| `freshUntil` | ISO 8601 | Snapshot validity horizon; after it, re-verify live (L3). |
| `resolve` | URL | IAASO-0002 resolution endpoint for the subject (L3). |
| `statusEndpoint` | URL? | IAASO-0002 status object. |
| `verify` | URL? | Human verifier page. |

Payloads MUST NOT contain floating-point numbers, so that JCS canonicalization
is reproducible by minimal verifiers (e.g. a sorted-key `JSON.stringify` in a
browser). All timestamps are RFC 3339/ISO 8601 UTC strings.

### 4.2 SVG container

The signed envelope is embedded verbatim (XML-escaped) in
`<metadata id="uuaid-badge" data-spec="IAASO-0003">…</metadata>`. The root
`<svg>` carries `data-uuaid` and `data-fingerprint` attributes; `<title>`/`<desc>`
restate the UUAID and fingerprint for accessibility. A visible caption row
renders the short UUAID and `⛓ <fingerprint>`, where **fingerprint** is the
first 16 hex characters of `payloadHash`.

Verifiers MUST extract the envelope from `<metadata id="uuaid-badge">` and MUST
NOT trust any visually-rendered text; only the signed payload is authoritative.
Note that some hosts sanitize `<metadata>` when rendering SVG via `<img>`; the
proof survives in the *file*, so badges MUST be verified from the SVG source, not
a re-rendered raster.

### 4.3 Trust root

The registry publishes its badge-signing public key(s) at:

- `GET /.well-known/uuaid-registry.json`
- `GET /iaaso/v1/trust/registry-key`

returning `{ spec, hybrid, provisioned, environment, keys[], note }` where each
`keys[]` entry is `{ keyId, alg, transitionClass, publicKey }`. Relying parties
**MUST pin** these keys before treating a badge as an identity claim.
`provisioned:false` marks a development key that is publicly derivable and MUST
NOT be trusted. A production registry MUST provision real keys (see §7 of the
reference implementation) and MUST refuse to issue badges under a development key.

> **Normative, and the reason for it.** A badge envelope carries the signer's own
> `publicKey`. Every other check in §5 — well-formedness, the `payloadHash` bind,
> signature validity, even a valid ML-DSA-65 signature — passes for a badge that
> anybody minted with a fresh keypair and a copied `keyId`. The pin is the *only*
> step that distinguishes "this registry issued it" from "this object is internally
> consistent". A verifier that cannot obtain the trusted key set MUST fail closed:
> it MUST NOT report an issuer-signed level, and MUST report the reason. An
> unpinned structural inspection is permitted only as an explicitly named,
> non-default mode, and its result MUST NOT be presented as a trust decision.
>
> This was raised from SHOULD to MUST on 2026-08-25 after the reference
> implementation was shown to return `ok:true, level:"L1-signed", pqProtected:true`
> for a self-minted forgery when the caller omitted the pin. Optional security is
> decoration; the specification should not have made it optional either.

## 5. Verification levels

A verifier reports the highest level it establishes:

- **L0 — well-formed:** parses; carries the required §4.1 fields and ≥1 signature.
- **L0-selfsigned — structurally valid, issuer unknown:** the payload binds and the
  signatures verify against the keys carried *inside the envelope*, but the signer
  is not a pinned registry key (§4.3), or no pin was supplied. This is the level a
  forgery reaches. It MUST NOT be reported as issuer-signed, and it MUST NOT be
  rendered with language implying the registry vouched for anything.
- **L1 — issuer-signed:** L0 well-formedness plus a `payloadHash` that binds the
  payload, every signature verifying, **and** a signer that matches a pinned
  registry key (§4.3). Tamper-evidence *and* origin. Without the pin a verifier
  reports L0-selfsigned, never L1.
- **L2 — bound (proof-of-possession):** in addition to L1, the presenter proved
  control of `subject.presentationKey` by answering a fresh challenge (§6). This
  defeats a copied bearer badge.
- **L3 — live:** in addition, the subject was re-resolved (IAASO-0002) and the
  live status has not regressed (no revocation/expiry/ suspension since
  `issuedAt`, and no badge credential is now revoked/expired).

A verifier MUST treat a badge as fully trusted for a cross-boundary action only
at **L2 + L3** (bound and live). L1 alone is sufficient for display or for a
low-risk, revocation-tolerant decision.

### 5.1 Name claims are not identity claims

`subject.displayName` and `subject.controller` are supplied by whoever registered
the subject. A registry signature attests that the registry *issued* the badge; on
its own it attests nothing about the bearer's entitlement to the name printed on
it. Issuers therefore MUST carry `subject.nameVerified` (boolean) in the signed
payload, `true` only where the issuer verified that entitlement out of band, and
verifiers MUST treat an absent field as `false`.

A verifier that displays `displayName` or `controller` MUST also surface the
`nameVerified` state. Because `nameVerified` lives inside the signed payload, a
forger can set it — it carries meaning only once the issuer is pinned (§4.3), and
a verifier MUST NOT read it before that check has passed.

Issuers SHOULD additionally refuse, at registration, names that assert a
verification status the issuer did not confer, and names containing marks the
issuer has reserved. Such a denylist is a mitigation, not a control: it does not
survive homoglyphs and it is not an adjudication of trademark. `nameVerified` is
the control; the denylist only reduces how often the honest answer is `false` next
to a name that looks official.

## 6. Presentation & challenge–response protocol

Proof-of-possession binds the *presenter* to the badge's subject key, so a badge
cannot be replayed by anyone who merely copied the SVG.

1. **Challenge (RP → agent).** The RP mints
   `{ "@type":"UUAIDBadgeChallenge", nonce, audience, subject?, issuedAt, expiresAt }`
   with ≥16 bytes of `nonce` entropy and a short TTL (default 300 s). The RP
   SHOULD mint its own challenge; the registry offers
   `POST /iaaso/v1/badge/challenge` (returning a registry-sealed challenge) as a
   convenience for RPs that cannot.
2. **Response (agent → RP).** The agent signs `JCS(challenge)` with its
   presentation key, returning `{ alg, publicKey, keyId, signature, created }`.
3. **Verify (RP).** The RP checks, in addition to the L1 badge checks:
   `subject-bound` (badge carries a presentation key), `challenge-fresh`
   (`now ≤ expiresAt`), `audience` (matches the RP), `challenge-subject`
   (matches the badge subject if the challenge bound one), `key-binding`
   (response `publicKey` == `subject.presentationKey.publicKey`), and
   `possession` (the response signature verifies over `JCS(challenge)`).

The RP MUST reject a response whose nonce it has already accepted within the TTL
(replay), and MUST reject an expired challenge. `audience` binding prevents a
proof captured by one RP from being replayed to another.

Convenience endpoint: `POST /iaaso/v1/badge/present/verify` performs the full
L1+L2+L3 check server-side (accepting either a plain or registry-sealed
challenge). It is a helper, not a trust requirement — the protocol is fully
verifiable offline by the RP.

## 7. Quantum readiness

Because a badge is a **long-lived attestation**, it must resist *harvest-now,
forge-later*: an adversary who records a badge today and acquires a
cryptographically-relevant quantum computer later MUST NOT be able to forge one.

Badges are therefore signed with a **hybrid** signature set:

| Algorithm | Role | `transitionClass` |
|---|---|---|
| Ed25519 | classical; verifiable everywhere today (incl. WebCrypto) | `classical` |
| ML-DSA-65 (FIPS 204) | post-quantum; unforgeable under Shor | `pqcPreferred` |
| SLH-DSA-128s | reserved | — |

Signing and verification are per ADR-002 / `/iaaso/v1/crypto-inventory`. A
hybrid badge carries one signature of each algorithm over the **same**
`JCS(payload)`. Rules:

- An issuer that has provisioned a PQ key MUST sign hybrid.
- `verifyEnvelope` requires **every** present signature to verify (`valid`
  ⇔ all verified). A verifier that trusts only PQ MAY additionally require an
  `ml-dsa-65` signature and treat its validity as authoritative; the reference
  verifier surfaces this as the `pq-signature` check and a `pqProtected` flag.
- Verifiers that cannot evaluate ML-DSA-65 (e.g. today's browser WebCrypto, which
  has no ML-DSA) MUST verify the classical signature, MUST report the PQ
  signature as present-but-unverified, and MUST NOT report full quantum
  assurance. `uuaid verify-badge` and `/iaaso/v1/badge/verify` verify both.

Key material: an ML-DSA-65 keypair is represented by its 32-byte seed
(`keygen(seed)` re-derives the ~4 KB secret key), so registry key storage stays
compact; the ~1952-byte public key is published alongside the Ed25519 key at
§4.3 and embedded in each PQ signature.

## 8. Security considerations

- **Bearer copy.** A badge without a presentation key (L1) is copyable; anyone
  holding the SVG can present it. Bind sensitive decisions to **L2**.
- **Snapshot staleness.** A badge reflects status at `issuedAt`. Revocation after
  issue is invisible to offline L1/L2; `freshUntil` bounds the window and **L3**
  catches regressions. RPs SHOULD run L3 for consequential actions.
- **Key compromise / rotation.** Registry keys are pinned by `keyId`; rotation
  publishes a new `keyId` at §4.3 while retaining old entries until their badges'
  `freshUntil` elapse. A compromised registry key can forge L1 badges until
  rotated — hence the PQ half and short `freshUntil`.
- **Downgrade.** A verifier MUST NOT accept a hybrid-capable issuer's badge that
  is missing the PQ signature once the issuer advertises `hybrid:true`.
- **Development keys.** `provisioned:false` keys provide zero authenticity and
  MUST be rejected by production RPs.

## 9. Privacy considerations

A badge discloses the subject UUAID, display name, controller, and credential
metadata to anyone who receives it — issue only what the presentation context
needs. Verification (L0–L2) is fully offline and leaks nothing; L3 and key
pinning contact the registry and thus reveal that a verification occurred. RPs
concerned with issuer-side observation MAY pin keys out-of-band and skip live
checks, trading revocation freshness for privacy.

## 10. Relationship to other IAASO work

- **IAASO-0001** defines the UUAID the badge is about.
- **IAASO-0002** provides `resolve`/`status`/`verify` — the badge's L3 backing
  and the `credentials[]` it snapshots.
- **did:uuaid** — a badge is a concrete verifiable presentation of the subject a
  DID document describes; a future revision MAY express the badge as a W3C
  Verifiable Presentation.

## 11. Media types & endpoints (reference)

- Badge SVG: `GET /badge/agent/{uuaid}/verifiable.svg` → `image/svg+xml`
- Badge JSON: `GET /iaaso/v1/badge/{uuaid}` → the signed envelope
- Verify: `POST /iaaso/v1/badge/verify` `{ badge, live? }`
- Challenge: `POST /iaaso/v1/badge/challenge` `{ audience, subject?, ttl_seconds? }`
- Presentation verify: `POST /iaaso/v1/badge/present/verify` `{ badge, challenge, proof, audience? }`
- Trust root: `GET /.well-known/uuaid-registry.json`

## 12. References

RFC 2119, RFC 3339, RFC 8785 (JCS), FIPS 204 (ML-DSA), FIPS 205 (SLH-DSA),
W3C Verifiable Credentials Data Model 2.0, IAASO-0001, IAASO-0002, ADR-002.
