[← Standards registrations](README.md)

# IAASO-0004 — Media Provenance & Attribution Protocol

- **Status:** Draft — proposal `019fef6e-a73e-7ce1-96da-1d838ce39755` OPEN before the standards-council (governance event 479, submitted by participant aadhan-a1, 2026-08-11)
- **Series:** IAASO (International Autonomous Agents Standards Organization)
- **Depends on:** IAASO-0001 (UAP identifiers), IAASO-0002 (Public Resolution & Verification), IAASO-0003 (Verifiable Badge & Presentation Protocol), ADR-002 (crypto-agility)
- **Reference implementation:** `@uuaid/provenance`, `apps/api` (`provenance.ts`), `uuaid sign-media` / `uuaid verify-media` / `uuaid verify-pdf`, `verify-provenance.html`

## 1. Abstract

A **Media Provenance Manifest** is a portable, cryptographically signed
statement of *who or what produced a piece of media*, carried inside the file
itself (PNG, JPEG) or alongside it (sidecar, any file type). It answers the
question C2PA popularised — "where did this come from?" — but binds the
answer to a **UUAID subject**: the manifest is signed by the subject's own
key, the same key model IAASO-0003 uses for badge presentation keys, so a
relying party that already trusts the UUAID registry for agent identity gets
media attribution for free.

A companion profile (§6) covers **signed PDFs**: an independent,
from-scratch cryptographic verifier for PKCS#7/PAdES signatures, plus
detection and verification of the ESigPQSeal post-quantum hybrid seal
(Ed25519 + ML-DSA-65) that e-signature implementations may embed. Both media
paths converge on the same four-level verification ladder (§5) and the same
trust model (§1's non-negotiable below).

**The registry VERIFIES, it never issues.** Provenance manifests are signed
by the subject — an agent, camera, or AI generator — client-side, using
`@uuaid/provenance` or the `uuaid` CLI. There is no registry-signing
endpoint for provenance and no new writer to `signing_keys` or any trust
store; registry-side code is read-only against the database.

## 2. Motivation

AI-generated and AI-modified media is now routine, and the party that matters
is rarely visible in the pixels: a camera, an AI model, or an agent produced
the file, and downstream consumers have no portable, verifiable way to ask
"which one, and can you prove it?" IAASO-0002 gives a live resolution surface
and IAASO-0003 gives a signed presentation of an *agent's* identity, but
neither attaches a claim to a *piece of content*. This standard closes that
gap: a manifest travels with the media, is signed by the producing subject's
own key, and is verifiable offline for tamper-evidence and online for
subject liveness — the same pattern IAASO-0003 established for badges,
applied to content instead of identity.

C2PA (the Coalition for Content Provenance and Authenticity) addresses
adjacent ground with a heavier, JUMBF/COSE-based container. This standard
does not attempt to supplant it: §1.2's C2PA detection check identifies C2PA
manifests when present (informational only — never "validated"), and §10
records a COSE bridge as future work. Where C2PA asks "is this manifest
well-formed," IAASO-0004 additionally asks "does the signing key resolve to
a live UUAID subject" — the binding IAASO-0002/0003 already provide.

## 3. Terminology

| Term | Meaning |
|---|---|
| **Manifest** | A `ProvenanceManifest` (§4.1): subject, content hash, creation time, optional generator/claims. |
| **Sealed manifest** | The manifest wrapped in a `@uuaid/core` signature envelope: `{ payload, payloadHash, signatures[] }` over `JCS(manifest)` (§4.1). |
| **Subject** | The UUAID the manifest is about — the agent, camera, or generator that produced the media. |
| **Generator** | Optional manifest field naming the producing system: `ai-model`, `camera`, `software`, or `agent`. |
| **Claim** | A short free-text assertion in the manifest, e.g. `"ai-generated"`, `"camera-capture"`, `"human-authored"`. |
| **Content hash** | SHA-256 over the media's *normalized* bytes (§4.2) — the bytes with the provenance slot itself removed, so embedding a manifest never invalidates the hash it certifies. |
| **Embedded manifest** | A sealed manifest stored inside the media file (PNG `iTXt` chunk, JPEG APP11 segment). |
| **Sidecar manifest** | A sealed manifest stored in a separate file, covering the *entire*, unmodified media file's hash. |
| **C2PA detection** | A structural check for a C2PA manifest container (JUMBF in JPEG APP11, `caBX` chunk in PNG). Detection is not validation (§8). |
| **ESigPQSeal** | The hybrid Ed25519 + ML-DSA-65 post-quantum seal an e-signature implementation may embed in a signed PDF (§6). |
| **Relying party (RP)** | Whoever verifies a manifest or a signed PDF. |

The key words MUST, SHOULD, MAY are per RFC 2119.

## 4. Manifest format

### 4.1 `ProvenanceManifest` (normative)

```ts
interface ProvenanceManifest {
  spec: "uuaid-prov/1";
  subject: string;                       // uuaid:... (isValidUuaid)
  content: { alg: "sha256"; hash: string }; // 0x-hex over NORMALIZED bytes (§4.2)
  created_at: string;                    // ISO 8601 UTC
  generator?: { type: "ai-model" | "camera" | "software" | "agent";
                name?: string; version?: string };
  claims?: string[];                     // e.g. "ai-generated", "camera-capture", "human-authored"
}
```

The **sealed form** is a `@uuaid/core` signature envelope over
`JCS(manifest)` (RFC 8785 canonicalization), produced by
`sealEnvelope(manifest, signers)` and consumed by `verifyEnvelope` —
implementations MUST reuse `@uuaid/core`'s `sealEnvelope`/`verifyEnvelope`
and MUST NOT reimplement envelope sealing or verification:

```ts
sealEnvelope(manifest, signers) → {
  payload,                 // the ProvenanceManifest above
  payloadHash,             // "0x" + sha256(JCS(payload)) — NORMATIVE, MUST be checked
  signatures: [{ alg, keyId, publicKey, signature, created }],
}
```

Every field above is REQUIRED. `payloadHash` binds the envelope to its payload:
a verifier MUST recompute `sha256(JCS(payload))` and reject the envelope when it
differs, before or alongside signature verification. The signature field is named
`signature` (not `sig`), and `keyId` is required, not optional — this is the exact
shape `@uuaid/core` produces and both reference verifiers demand; an envelope of
any other shape fails `manifest-parse` and is `invalid`.

An Ed25519 signature is REQUIRED. An ML-DSA-65 (FIPS 204) signature is
OPTIONAL; a hybrid pair (both) is RECOMMENDED for the same harvest-now,
forge-later reasons IAASO-0003 §7 gives for badges. `publicKey` and `signature`
are hex-encoded; `created` is an ISO 8601 timestamp.

A verifier MUST bound the nesting depth of `payload` (32 levels is ample for this
schema, whose deepest normative field is one level down) and reject anything
deeper. JCS canonicalization is recursive: a payload of a few thousand levels is
only ~10 KB on the wire — far inside the size cap below — and exhausts the call
stack of a recursive canonicalizer, turning a verify request into an unhandled
error rather than a verdict.

The serialized embed form is `JSON.stringify(sealed)` as UTF-8,
**uncompressed**, and MUST NOT exceed **60,000 bytes**. Implementations MUST
enforce this as a hard cap on both embedding and extraction — reject larger
manifests rather than truncate or compress them. The cap applies to a
**detached (sidecar) manifest** exactly as it does to an embedded one: a
verifier that accepts a sidecar over the wire MUST measure the serialized
manifest and reject an oversized one before verifying it.

`signatures` MUST contain at least one and at most **8** entries. Verification
cost is linear in both the signature count and the payload size, so an
unbounded array turns a single verify request into an O(|signatures| ×
|payload|) CPU burn; a verifier MUST reject an envelope that exceeds the cap
rather than verify the first N. A verifier SHOULD check each signature exactly
once and reuse the verdict, rather than re-canonicalizing the payload per
algorithm.

### 4.2 Embedding and hash-exclusion (normative)

The content hash a manifest certifies is computed over the file **with the
provenance slot itself removed**, so that embedding the manifest does not
invalidate the hash it carries. Exclusion is **by identity, not by byte
offset** — an implementation MUST locate and exclude the provenance
container structurally (by chunk type / keyword, or by segment marker /
header), never by assuming a fixed position.

A conforming file carries **exactly one** provenance slot. Because exclusion
is by identity it removes *every* matching container, while extraction reads
only the first: a second slot would therefore be unbounded, unread content
that the content hash does not commit to, riding inside a file that still
verified. A verifier MUST fail the `structure` check when more than one
provenance slot is present, and an embedder MUST replace any existing slot
rather than append a second one.

- **PNG** (magic `89 50 4E 47 0D 0A 1A 0A`): the manifest lives in an `iTXt`
  chunk with keyword `uuaidProvenance`, `compressionFlag 0`, and no
  language or translated-keyword fields. The **normalized bytes** are the
  8-byte PNG signature, followed by every chunk (raw: `length ‖ type ‖ data
  ‖ crc`) **except** any `iTXt` chunk whose keyword equals
  `uuaidProvenance`, followed by **any bytes trailing the last chunk**.
  Those trailing bytes MUST be hashed and an embedder MUST preserve them:
  a PNG proper ends at `IEND`, but appending data is trivial and every
  viewer, CDN and download passes it on as part of the file, so a hash that
  stopped at `IEND` would let content be appended to a signed image while
  it still verified — the PNG form of the appended-content attack §6.1's
  `coverage` check catches for PDFs — and would leave PNG and JPEG (which
  hashes its whole tail) with different coverage guarantees.
  Embedding inserts the manifest chunk immediately after
  `IHDR`. Implementations MUST hand-roll the chunk codec and CRC-32
  (standard table) rather than depend on a PNG library. A chunk whose CRC-32
  does not match SHOULD be reported (e.g. in the `structure` check detail)
  but MUST NOT by itself fail verification: the content hash is the
  authoritative tamper signal, and it commits to those exact bytes.
- **JPEG** (starts `FF D8`): the manifest lives in an APP11 (`0xFFEB`)
  segment whose payload begins with the ASCII marker `UUAID-PROV\0`
  followed by the manifest JSON. The **normalized bytes** are the whole
  file **except** any APP11 segment carrying that marker. Embedding inserts
  the segment immediately after SOI, before any other segment. A segment
  payload is capped at 65,533 bytes; the sealed manifest MUST fit in a
  single segment (a hybrid-sealed manifest is ≈10 KB in practice, well
  inside the cap).
- **Sidecar** (any file type): the manifest travels detached from the
  media. `content.hash` is the SHA-256 of the **entire** file, unmodified —
  there is no exclusion to perform because nothing is embedded.
- **C2PA detection** is a separate, informational structural check, never
  reported as "validated": in JPEG, any APP11 segment whose payload is a
  JUMBF box (`JP`/`jumb` boxes, ASCII `c2pa` present); in PNG, a chunk of
  type `caBX`. Implementations MUST report this as a boolean
  `c2pa_detected` and MUST NOT imply that detecting a C2PA container
  constitutes verifying it.

### 4.3 Verification checks (image path)

A conforming verifier reports the following stable, spec-referenced check
ids for the image path: `structure`, `manifest-parse`, `manifest-schema`,
`content-hash`, `signature`, `pq-signature` (present only when an ML-DSA-65
signature is included), and `subject-format`. When verification is
performed through the registry API (§11), the route additionally reports
`uuaid-binding` (L2, §5) and `subject-live` (L3, §5).

A check result is **tri-state**: `true` (evaluated and holds), `false`
(evaluated and failed), or `null` (not applicable at the level actually
achieved). The distinction is normative for `uuaid-binding`: a key the
registry has never seen is an *absence* of corroboration and reports `null`,
leaving an honest L1 verdict intact, whereas a key the registry attributes to
a *different* subject — or to more than one — is *contradictory* evidence and
MUST report `false`. Collapsing the two forces a choice between an unusable
L1 and a `verified: true` printed beside a failing check.

**Independent implementations MUST normalize the identical byte set.** A
second verifier that parses containers more permissively than the reference
implementation — walking past a JPEG SOS marker into entropy-coded scan data,
or matching an `iTXt` keyword without requiring the full chunk layout — will
exclude structures the reference implementation hashes, and will report
`verified` over bytes every conforming verifier rejects. The divergence is
precisely where content hides, so a browser-side or client-side verifier is
conformant only if it stops where the reference parser stops and throws where
it throws.

The same rule binds the *envelope*, not only the container: a verifier MUST
apply the whole envelope rule of §4.1 and §5 — every signature verifies, the
signature count is within the cap, each signature carries the required fields,
and the payload is within the depth bound — before reporting `signature` as
passing. Verifying the first signature (or the first Ed25519 signature) and
ignoring the rest reports `verified` over an envelope carrying entries the
reference implementation counts as failures, which is the same fail-open
divergence by a different route.

## 5. Verification levels

A verifier reports the **highest** level it establishes; `verified: true`
if and only if no check it evaluated failed — that is, every check applicable
at the achieved level passes and none of the higher-level checks it attempted
returned contradictory evidence.

A verifier MUST NOT present a `subject` as an attribution unless
`uuaid-binding` passed. Anyone can sign a manifest naming any UUAID, so an
unbound `subject` is a self-claim by whoever held the signing key; consumers
render `verified` and `subject` as a single statement, so an unbound subject
that ships beside a passing verdict is a misattribution primitive. Report the
claimed value as part of the `subject-format` check detail (or label it
explicitly as self-asserted, as an offline verifier must), never as a bare
`subject` field.

- **L0 — well-formed:** the manifest (or PDF signature structure) parses
  and its schema is valid.
- **L1 — signed:** every signature in the sealed manifest verifies, the
  envelope's `payloadHash` binds its payload, `content.hash` matches the
  recomputed, exclusion-normalized hash of the media, **and** `subject` is a
  well-formed UUAID (`subject-format`). This is tamper-evidence: the manifest
  has not been altered and it genuinely describes this content. All four are
  hard gates — a manifest naming a subject that is not a UUAID names no
  identity to attribute anything to, so it is L0, not L1, however valid its
  signature.
- **L2 — bound:** in addition to L1, the manifest's (or seal's) embedded
  Ed25519 public key — hex-encoded — resolves against an `agora_profile_keys`
  row (the subject's registered presentation keys, per IAASO-0003). For
  images, the resolved row's UUAID MUST equal `manifest.subject`, or the
  `uuaid-binding` check fails and L2 is not achieved. Unlike an IAASO-0003
  badge, a provenance manifest is signed by the subject itself, so the
  signature already constitutes proof of possession of the signing key —
  no separate challenge-response protocol is required to reach L2.
- **L3 — live:** in addition to L2, the subject resolves as ACTIVE — not
  superseded and not tombstoned — via the same resolve semantics IAASO-0002
  defines (reference implementation: `routes.ts` resolve handler). A
  manifest whose subject has since been superseded still parses and
  verifies at L1/L2; L3 is what catches the regression.

The PDF profile (§6) uses the same ladder but **stops at L1** in this
revision. L1 means "math-valid": the classical signature and, if present, the
ESigPQSeal both verify. L2 and L3 are NOT reachable for a PDF, because the
only candidate binding — the seal's Ed25519 key resolved against
`agora_profile_keys` — is not evidence of ownership: registering a key proves
control of the *agent*, never possession of the *key*, and every sealed PDF
publishes its seal key in plaintext. Unlike an image manifest, a PDF asserts
no subject of its own and signs no statement about one, so there is nothing to
cross-check a registry row against. A conforming verifier therefore MUST NOT
synthesize a subject from a PDF key binding; it reports the situation as a
`uuaid-binding` check with `pass: null`.

L2/L3 become reachable for PDFs once the binding is self-evidencing — either
the signer asserts its own UUAID inside the seal payload (so the seal's
signature covers the claim), or key registration gains a proof-of-possession
challenge. §10 tracks both.

## 6. PDF signature verification profile

Signed PDFs — most commonly e-signature output — are a distinct media type
with their own signature container (PKCS#7/PAdES `/ByteRange` +
`/Contents`), not a manifest. Implementations MUST implement PDF
verification **independently** of any signer's own verification code: a
verification authority sharing code (and bugs) with the signer it verifies
is not independent, and this also sidesteps the node-forge CVE class
(VU#725167) that affects at least one signer implementation in this
ecosystem. The reference implementation verifies with `pkijs` rather than
`node-forge`.

### 6.1 Classical (PKCS#7/PAdES) verification

- **Scan every** `/ByteRange [...] /Contents <hex>` pair in the document,
  not just the first — a PDF may carry multiple signatures via incremental
  update, and a verifier MUST return an array of per-signature results.
- **The first offset MUST be 0.** For `/ByteRange [a b c d]`, a verifier
  MUST fail the `byte-range` check unless `a == 0` (as PAdES and every
  mainstream producer require). A non-zero `a` leaves the first `a` bytes —
  which a reader renders — covered by no digest and named by no other
  check: `coverage` only guards the tail, so without this term such a
  document verifies `ok:true` with unsigned front matter, and a
  post-quantum seal placed below `a` would satisfy the "inside the signed
  range" test in §6.2 while being protected by nothing.
- **Trim** the `/Contents` hex blob to the length its own DER header
  declares. Implementations MUST NOT strip trailing zero bytes to find the
  end of the signature — roughly 1 in 256 legitimately-generated signatures
  end in a `0x00` byte, and trimming on that basis falsely rejects them.
- **Coverage:** the *latest* signature's `/ByteRange` MUST reach end-of-file
  (no bytes appended after the last signed region). A document with bytes
  appended past the final signature's coverage MUST fail the `coverage`
  check — this is the appended-content attack: content added after signing
  that no signature protects.
- Parse the `/Contents` DER as a CMS `ContentInfo` → `SignedData`
  (`pkijs`). Recompute SHA-256 over the `/ByteRange`-covered bytes and
  compare it, in constant time, against the signed `messageDigest`
  attribute. Verify the signature over the re-tagged `signedAttrs` SET
  against the embedded signer certificate's public key; both RSA
  (PKCS#1 v1.5) and ECDSA signer keys MUST be accepted.
- Report, per signature: signer common name and organization, certificate
  serial number, validity window, and the certificate's SHA-256
  fingerprint.
- **Math ≠ trust.** A valid signature proves the document has not been
  altered since it was signed and that the signature was produced by the
  private key matching the embedded certificate. It does **not** establish
  that the certificate chains to any trust anchor, that it has not been
  revoked, or that the signer is who the certificate claims. Verifiers MUST
  say so in their output, not merely in documentation.
- **Signer certificate resolution:** the `SignerIdentifier` MUST be
  resolved as CMS defines it — `issuerAndSerialNumber` matched on issuer
  **and** serial (a serial is unique only within an issuer), or the
  `subjectKeyIdentifier` alternative matched against the certificate's
  SubjectKeyIdentifier extension. A verifier MUST NOT fall back to "the
  first certificate in the set" when nothing matches: chain-bundled CMS
  routinely places an intermediate first, and verifying against it reports
  a valid document as forged, under the wrong signer's name. When no
  certificate matches, report that the signer certificate was not found.
- **RFC 3161 timestamp binding:** if a SignerInfo carries an unsigned
  `id-aa-timeStampToken` attribute, the verifier MUST enforce, as a hard
  failure on mismatch, that the token's `messageImprint` equals
  SHA-256(`signatureValue`). Absence of a timestamp is not a failure.
  This profile verifies the token's **binding only** — not the TSA's own
  signature, nor its certificate. A verifier that uses the token's
  `genTime` as the reference clock for `cert-window` MUST therefore label
  that time as unverified and self-asserted: whoever can produce the
  document's signature can attach a self-made token with any `genTime` and
  move `cert-window` either way. This is why `cert-window` is
  informational and never gates the verdict.

Check ids for the PDF path: `byte-range`, `coverage`, `contents-der`,
`digest`, `signature`, `cert-window` (informational: certificate validity
window versus the RFC 3161 time, when present), `timestamp-binding`. A
seal adds `pq-seal-structure`, `pq-seal-signature`, `pq-seal-covered`
(§6.2). There is no `subject-live` on this path and no `subject` in the
response: the PDF profile stops at L1 (§5, §6.2), so a route that finds an
ESigPQSeal reports `uuaid-binding` with `pass: null` — "not evaluated for
PDFs" — and never resolves a subject to check the liveness of.

`cert-window` MUST NOT gate `verified`. A verifier that folds it into the
verdict rule ("no evaluated check failed", §5) reports `verified: false`
beside `level: "L1-signed"` for every archived document whose signer
certificate has since expired — the normal case for a document older than
its certificate's lifetime — and hands an attacker who can produce a
signature a self-made `genTime` that moves the verdict either way.
Implementations report it as `pass: null` (tri-state, §4.3) with the outcome
stated in the check's detail text, or exclude it from the verdict rule
explicitly; they do not emit it as an ordinary gating check.

### 6.2 ESigPQSeal (post-quantum hybrid seal)

An e-signature implementation MAY embed a post-quantum hybrid seal alongside
its classical signature, as a PDF object of the form
`/Type/ESigPQSeal/V 1/Seal(<base64>)`. The seal is a small canonical-JSON
object — `{ v, alg: "hybrid-ed25519-ml-dsa-65", over: "sha256", digest,
coveredBytes, signedAt, keyId, keys: {ed25519, mldsa65, mldsa65Fpr},
sig: {ed25519, mldsa65} }` — signed with **both** an Ed25519 (classical) and
an ML-DSA-65 (FIPS 204, post-quantum) signature over the same canonical
bytes (the seal minus `sig`), so digest, covered length, keys, timestamp,
and key id are all bound together under both schemes.

A verifier MUST, when a seal is present:

- Recompute SHA-256 over the first `coveredBytes` bytes of the document and
  compare it to the seal's `digest` (document binding).
- Verify **both** the Ed25519 signature and the ML-DSA-65 signature over the
  seal payload with `@noble/curves`/`@noble/post-quantum`, per the exact
  field layout in esig-suite's `pq-seal.ts` / `pq-verify.ts` — implementers
  MUST read those two files and replicate their checks, including the
  fingerprint self-consistency check (`mldsa65Fpr == sha256(mldsa65
  pubkey)`) and the key-id self-consistency check.
- Confirm the seal's covered region lies **inside** the classically-signed
  `/ByteRange` region (`pq-seal-covered`) — a seal covering bytes the
  classical signature does not protect is not actually protected by it.

Check ids: `pq-seal-structure`, `pq-seal-signature`, `pq-seal-covered`.

**Why a PDF stops at L1 (and what would change that).** The seal's Ed25519
public key looks like the natural UUAID binding hook for a signed PDF, and an
earlier draft of this document treated it as one. It is not sufficient on its
own. That key is published in plaintext inside every sealed document, and an
`agora_profile_keys` row only records an assertion by an agent's controller —
no challenge proves the registrant holds the private key, and nothing stops a
second party registering the same key. Resolving the seal key through that
table would therefore let anyone who can register a key claim authorship of
a third party's genuinely signed documents. An image manifest is immune to
the same registry weakness because the manifest *names its own subject and
signs that statement*, so the registry row only corroborates a claim the
signer already proved; a PDF makes no such claim. A verifier MUST NOT
attribute a PDF on the strength of a key binding alone (§5).

Two changes each make the binding self-evidencing, and either one restores
L2/L3 for PDFs:

- **Signer-asserted UUAID in the seal.** An e-signature implementation
  SHOULD carry the signer's UUAID *inside* the ESigPQSeal payload, so the
  seal's own signature covers the claim. The registry lookup then plays the
  same corroborating role it plays for images.
- **Proof of possession at registration.** A registry SHOULD require a
  signature over a server-issued challenge before binding a public key to an
  agent, and SHOULD enforce uniqueness on the active public key.

Registering the ESigPQSeal key as a subject profile key remains useful and is
still RECOMMENDED — it is a prerequisite for L2 under either change — but on
its own it does not raise a PDF above L1.

## 7. Quantum readiness

Because a provenance manifest or a signed PDF may need to resist scrutiny
long after signing, both paths follow IAASO-0003's harvest-now,
forge-later posture:

- **Manifests:** Ed25519 is REQUIRED; ML-DSA-65 is OPTIONAL and
  RECOMMENDED. `verifyEnvelope` requires every present signature to
  verify — a manifest carrying a broken PQ signature alongside a valid
  Ed25519 one MUST NOT be reported as fully verified; the reference
  verifier surfaces this via the `pq-signature` check and a `pqProtected`
  flag on the result.
- **PDFs:** an ESigPQSeal, when present, is always the hybrid pair
  (Ed25519 + ML-DSA-65) by construction (§6.2); there is no PQ-optional
  seal.
- **Browser verification limits:** today's WebCrypto has no ML-DSA
  primitive. A browser-side verifier (§11) MUST verify the classical
  Ed25519 signature, MUST detect and label a present ML-DSA-65 signature as
  "present, verified server-side only," and MUST NOT claim full quantum
  assurance for a purely client-side check. Since L1 requires *every*
  present signature to verify, such a verifier MUST NOT report L1 while an
  ML-DSA-65 signature is unverified: it reports an explicitly incomplete
  outcome ("classical half verified — server-side verification required"),
  which is neither a pass nor a failure. Full dual verification (both
  algorithms) is available server-side via the registry API.

## 8. Security considerations

- **Parser hardening.** Image parsing is a chunk/segment *structural* walk
  only — implementations MUST NOT decode pixel data at any point. PNG and
  JPEG codecs are hand-rolled (§4.2) specifically to avoid depending on a
  general-purpose image-decoding library's attack surface for a task that
  only needs to locate chunk/segment boundaries.
- **Size caps.** The 60,000-byte manifest cap (§4.1) applies on both embed
  and extract, and to a manifest supplied detached over the wire. The
  signature-count cap (§4.1, 8) applies wherever an envelope is verified.
  API routes additionally cap decoded request bodies at 20 MB and reject
  oversized input before parsing.
- **Unbounded work from a single request.** Verification runs on a public,
  unauthenticated route, and its expensive steps are synchronous CPU: one
  request that forces super-linear work blocks the whole event loop, so a
  rate limit does not contain it. Every count and length a *document* gets
  to declare MUST be capped independently of the body size — in particular
  the number of `/ByteRange` declarations (the reference implementation
  accepts at most 32, de-duplicated), the size of each declared `/Contents`
  region (512 KB) *checked before it is scanned*, and the number of
  signatures in an envelope. A verifier MUST also confirm the container is
  what it claims to be (`%PDF-` header) before scanning it, and SHOULD
  impose a wall-clock budget on the whole verification as a backstop.
- **Smuggling through an excluded slot.** Anything the content hash excludes
  is attacker-controlled cargo unless it is also *read and validated*. This
  is why exactly one provenance slot is permitted (§4.2): the asymmetry
  between "exclude every match" and "read the first match" is the bug class,
  not the exclusion itself.
- **Appended-content attack.** A PDF with bytes appended after its last
  signature's `/ByteRange` coverage is not protected by that signature over
  the appended region; the `coverage` check (§6.1) exists specifically to
  catch this and MUST be enforced as a hard failure.
- **DER-trimming trap.** Trimming a `/Contents` hex blob by stripping
  trailing zero bytes instead of respecting the DER-declared length
  produces roughly a 1-in-256 false-reject rate against otherwise-valid
  signatures (§6.1); implementations MUST use the declared length.
- **C2PA detection is not validation.** Detecting a JUMBF/`caBX` container
  says only that a C2PA-shaped structure is present; it says nothing about
  whether that structure's own signature verifies. A verifier MUST NOT
  represent `c2pa_detected: true` as "C2PA-verified."
- **Key registration is not proof of possession.** An `agora_profile_keys`
  row records that an agent's controller *asserted* a public key; it does not
  demonstrate that anyone holds the corresponding private key, and the table
  does not constrain a public key to a single agent. A verifier MUST NOT
  treat such a row as sole evidence of authorship — that is what makes the
  PDF path stop at L1 (§5). Where a row is used at all, it MUST fail closed
  when more than one agent claims the same active key: a contested key binds
  to nobody, and picking a row arbitrarily (an unordered `LIMIT 1`) hands the
  attribution to whichever row the database happened to return. Registries
  SHOULD add a proof-of-possession challenge at key registration and a
  uniqueness constraint on the active public key.
- **Key compromise / rotation.** A subject whose Ed25519 signing key is
  compromised can have forged manifests or seals produced under that key
  until the corresponding `agora_profile_keys` entry is deactivated. L3
  (§5) catches a *subject-level* regression (superseded/tombstoned) but
  does not, on its own, detect a still-active subject whose key has leaked;
  operators SHOULD deactivate a compromised key's `agora_profile_keys` row
  promptly, which then fails `uuaid-binding` for any manifest signed under
  it going forward.
- **Development / self-issued PDF certificates.** As with any PKCS#7/PAdES
  verification, a self-issued signer certificate is its own trust root;
  establishing trust in *who* signed (versus *that* the signature is
  mathematically valid) is a deployment-level, out-of-band concern (§6.1,
  "math ≠ trust").
- **No registry-signing surface.** Because the registry never signs a
  provenance manifest or PDF seal (§1), there is no registry-side signing
  key whose compromise could forge attribution for content the registry
  did not itself produce — the entire trust chain for a manifest's *claim*
  rests on the subject's own key, which this standard only ever verifies.

## 9. Privacy considerations

- **No biometrics, no pixel inspection.** Verification never decodes image
  content; it inspects container structure and cryptographic material
  only.
- **Public by design.** An embedded manifest travels with the file and
  discloses the subject UUAID, generator metadata, and claims to anyone who
  receives that file — issue only what the presentation context needs, and
  prefer generic `claims` over identifying detail where possible.
- **Sidecar for deniability.** A sidecar manifest is not embedded in the
  media; a party may distribute the media without the manifest, and the
  manifest without the media, giving producers a way to withhold
  attribution from a given recipient without altering the underlying file.
- **Live checks reveal a lookup occurred.** L2/L3 (§5) contact the
  registry and therefore reveal, to the registry, that a verification took
  place — as with IAASO-0002/0003, a relying party concerned with
  registry-side observation MAY pin subject keys out-of-band and rely on
  offline L0/L1 checks, trading revocation/liveness freshness for privacy.

## 10. Relationship to other IAASO work

- **IAASO-0001** defines the UUAID the manifest's `subject` field names.
- **IAASO-0002** provides the resolve/status semantics L3 (§5) reuses to
  detect a superseded or tombstoned subject.
- **IAASO-0003** established the presentation-key model this standard binds
  to at L2: `agora_profile_keys` rows registered for badge presentation are
  the same rows a provenance manifest's embedded key resolves against.
  Registering a key for one purpose serves both. Note the limit that model
  carries (§8): a row is an assertion, not proof of possession, which is why
  it corroborates an image manifest's self-signed subject claim but cannot
  attribute a PDF on its own (§6.2).
- **C2PA.** This standard performs C2PA **detection only** (§4.2, §8) —
  identifying that a C2PA container is present, never validating its
  contents. A future revision MAY define a COSE bridge that lets a
  UUAID-signed manifest and a C2PA manifest cross-reference or co-verify
  the same asset; that bridge, full C2PA/COSE validation, XMP embedding,
  and video container support are all explicitly out of scope for this
  version (§8 of the design record).
- **esig-suite.** The PDF profile (§6) is written to verify e-signature
  output independently, and §6.2 records a standing recommendation that
  e-signature implementations register their ESigPQSeal key as a subject
  profile key. Adopting that recommendation in esig-suite itself is a
  separate change in that project's own lane, tracked outside this
  document.

## 11. Media types & endpoints (reference)

- Image manifest verify: `POST /iaaso/v1/provenance/verify`
  `{ media_b64?, manifest?, content_hash?, live? }` →
  `{ verified, level, subject?, format?, c2pa_detected?, checks[] }`
  (an embedded manifest is read from `media_b64`; a sidecar manifest is
  supplied via `manifest` together with either `content_hash` or
  `media_b64` for hash recomputation). `subject` is present only when
  `uuaid-binding` passed (§5); `checks[].pass` is tri-state.
- PDF verify: `POST /iaaso/v1/provenance/verify-pdf` `{ pdf_b64, live? }` →
  `{ verified, level, signatures[], pq_seal?, checks[] }`. No `subject`:
  the PDF path stops at L1 (§5, §6.2).
- CLI: `uuaid sign-media` (produce an embedded or sidecar sealed manifest),
  `uuaid verify-media` (local L0/L1, `--live` for L2/L3 against the API),
  `uuaid verify-pdf` (server-side verification of the same L1 profile).
- Web verifier: `verify-provenance.html` — drag-and-drop PNG/JPEG, in-browser
  L0/L1 (Ed25519 only, per §7 — but EVERY signature in the envelope, with an
  ML-DSA-65 entry deferred to the API rather than waved through), optional live
  L2/L3 via the API; PDFs are offered "verify on server" via `verify-pdf`, with
  no L2/L3 option, since the PDF path stops at L1 (§5, §6.2). Its container
  parsers and its envelope-shape rules mirror the reference implementation
  exactly, per §4.3.
- Both API routes are public, unscoped, and IP rate-limited, matching the
  IAASO-0003 badge-verify precedent — provenance verification is a public
  good, not a partner-gated operation.

## 12. References

RFC 2119, RFC 3339, RFC 3161 (Time-Stamp Protocol), RFC 5652 (CMS), RFC 8785
(JCS), FIPS 204 (ML-DSA), ISO/IEC 15948 (PNG), ISO/IEC 10918-1 (JPEG), C2PA
Technical Specification, VU#725167 (node-forge ASN.1 CVE class), IAASO-0001,
IAASO-0002, IAASO-0003, ADR-002.
