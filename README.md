# UAP — the Universal Agent Protocol

Open specifications for **permanent identity, encrypted portable memory, and
signed cross-domain interaction between AI agents**. Published by IAASO, the
International Autonomous Agents Standards Organization.

Everything here is crypto-agile by construction: explicit algorithm identifiers,
RFC 8785 (JCS) canonicalization, sha256 content hashes, and one hash-chained
ledger whose Merkle roots are anchored to Polygon mainnet.

Reference implementation: [`@uuaid/core`](https://www.npmjs.com/package/@uuaid/core),
[`@uuaid/cli`](https://www.npmjs.com/package/@uuaid/cli),
[`@uuaid/provenance`](https://www.npmjs.com/package/@uuaid/provenance) ·
live at [`api.uuaid.org`](https://api.uuaid.org/docs) ·
[uuaid.org](https://uuaid.org)

## Standards

| | Document | Status |
|---|---|---|
| **IAASO-0001** | [UAP — the Universal Agent Protocol v1](IAASO-0001-universal-agent-protocol.md) | Ratified. Identity, vault, and interaction envelopes. |
| **IAASO-0002** | [Public Resolution & Verification Protocol v1.1](IAASO-0002-public-resolution-verification-protocol.md) | Published; proposal before the standards-council. **v1.1 amends §6.3/§6.4 under ballot** — anchor submitters must be published and pinned. |
| **IAASO-0003** | [Verifiable Agent Badge & Presentation Protocol v1.1](IAASO-0003-verifiable-badge-and-presentation-protocol.md) | Draft v1.1, reference implementation shipped and deployed. |
| **IAASO-0004** | [Media Provenance & Attribution Protocol](IAASO-0004-media-provenance-and-attribution.md) | **Adopted** 2026-08-14 (standards-council ballot, approve 1 / reject 0 / abstain 1). |
| — | [The `did:uuaid` DID Method v0.1](did-method-uuaid.md) | Registered in the [W3C DID Extensions registry](https://w3c.github.io/did-extensions/methods/) (w3c/did-extensions#730, July 2026). Registered is not resolvable: DID-native resolution is not shipped, and today you resolve through the registry endpoint. |

Also registered: the IANA provisional URI scheme
[`uuaid:`](https://www.iana.org/assignments/uri-schemes/prov/uuaid) (July 2026,
CRI scheme number 1015).

## Start here

If you are implementing a **verifier** — the common case — read
[IAASO-0003 §4.3 and §5](IAASO-0003-verifiable-badge-and-presentation-protocol.md#43-trust-root)
first, and take one thing from it before anything else:

> A badge envelope carries the signer's own public key. Every structural check —
> well-formedness, the payload-hash bind, signature validity, even a valid
> post-quantum signature — passes for a badge that anybody minted with a fresh
> keypair and a copied `keyId`. **Pinning the issuer against a published root is
> the only step that turns a valid signature into an identity claim**, and a
> verifier that cannot pin MUST fail closed.

This was raised from SHOULD to MUST in v1.1 (2026-08-25) after our own reference
implementation was shown to accept a self-minted forgery as issuer-signed. The
write-up is at [uuaid.org/know-your-agent](https://uuaid.org/know-your-agent).

## Reporting a problem

Specification bugs: open an issue here. Vulnerabilities in the reference
implementation or the live registry: [security@uuaid.org](mailto:security@uuaid.org).
A finding that breaks a claim in these documents is more useful to us than a star.

## Licence

Apache-2.0 — see [LICENSE](LICENSE).
