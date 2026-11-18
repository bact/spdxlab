---
SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
SPDX-FileType: DOCUMENTATION
SPDX-License-Identifier: CC0-1.0
---

# SPDX 3: JSON-LD context makes standard processors misread strings

Reproduction for
[spdx/spdx-3-model#1167](https://github.com/spdx/spdx-3-model/issues/1167)
(point 1),
[spdx/spec-parser#204](https://github.com/spdx/spec-parser/issues/204) and
[spdx/spdx-3-model#1477](https://github.com/spdx/spdx-3-model/issues/1477).
Fix: bact/spec-parser branch
[`type-id-class`](https://github.com/bact/spec-parser/tree/type-id-class).

## The problem

The SPDX 3 spec says SPDX 3 JSON "may be parsed … using standard JSON-LD
libraries", and that SPDX data can be serialized in any RDF format. Standard
JSON-LD processors are what RDF tools use to read it: rdflib and pyld
(Python), Apache Jena with Titanium (Java), jsonld.js (JavaScript).

With the published context, these processors read some strings differently
from what SPDX means. Both cases have one cause: a string value is first
matched against the top-level context terms.

1. **Enumeration values.** An entry named like a top-level term expands to
   that term: `profileConformance: "extension"` gives the property
   `…/Core/extension`, not `…/ProfileIdentifierType/extension`. Same for
   `relationshipType: "createdBy"` and `externalIdentifierType:
   "requirementUID"` in 3.1-dev.
   A schema-valid document is affected.
2. **Element references.** The 93 class-valued properties (`createdBy`,
   `from`, `to`, `element`, …) are typed `"@type": "@vocab"`. A reference
   written as a relative IRI, such as `"Person"`, should resolve against the
   document base (`<base>Person`). With `@vocab` it is first matched as a term
   and expands to the SPDX class `…/Core/Person` instead. JSON-LD 1.1
   §4.2.3 warns about this: IRI values are "typically considered to be
   document-relative". The SPDX JSON Schema rejects relative IRIs, but they
   are valid JSON-LD that RDF tools may produce.

## The example documents

Both use base `https://example.org/doc/`.

[enum-value-matches-term.json](enum-value-matches-term.json): an
SpdxDocument that conforms to the `core` and `extension` profiles;
`profileConformance` should give two `ProfileIdentifierType` entries.

```json
{
  "type": "SpdxDocument",
  "spdxId": "https://example.org/doc/SpdxDocument",
  "creationInfo": "_:creationinfo",
  "profileConformance": ["core", "extension"],
  "rootElement": ["https://example.org/doc/Person"]
}
```

[relative-ref-matches-term.json](relative-ref-matches-term.json):
`createdBy` refers to the `Person` element by its relative `spdxId`, so it
should point to `https://example.org/doc/Person`.

```json
{
  "@context": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
  "@graph": [
    {
      "type": "CreationInfo",
      "@id": "_:creationinfo",
      "specVersion": "3.0.1",
      "created": "2026-11-18T00:00:00Z",
      "createdBy": ["Person"]
    },
    {
      "type": "Person",
      "spdxId": "Person",
      "name": "Jane Doe",
      "creationInfo": "_:creationinfo"
    }
  ]
}
```

## Validity

- `enum-value-matches-term.json` passes the SPDX 3.0.1 JSON Schema, yet fails
  SHACL (spdx3-validate 0.0.7): `extension` is read as the property
  `Core/extension`, which is not a `ProfileIdentifierType`. A valid document
  is rejected only because of the context.
- `relative-ref-matches-term.json` fails the JSON Schema on purpose: the
  schema allows only absolute IRIs (`^(?!_:).+:.+`) or blank nodes as ids and references. It is
  still valid JSON-LD that any RDF tool may produce or consume, and SHACL
  cannot catch the relative `spdxId`: `spdxId` is an alias of `@id`, so it is
  resolved before the RDF graph exists.

## See it (seconds)

```sh
cd context-vocab
python3 -m venv venv && venv/bin/pip install rdflib pyld
venv/bin/python quick.py                 # published 3.0.1, 3.1-dev, fixed
venv/bin/python quick.py NAME=CONTEXT ... # local or other contexts
```

`quick.py` reads each example unchanged except for its `@context`, then
prints what `createdBy` and `profileConformance` expand to (`spdx:` is the
terms namespace of the context in use). Contexts:

| Name | Context |
| --- | --- |
| 3.0.1 | <https://spdx.org/rdf/3.0.1/spdx-context.jsonld> |
| 3.1-dev | <https://spdx.github.io/spdx-spec/v3.1-dev/rdf/spdx-context.jsonld> |
| fixed | [fixed/spdx-context.jsonld](fixed/spdx-context.jsonld) |

Output (2026-11-18):

```text
3.0.1:
  enum-value-matches-term.json profileConformance (rdflib, pyld agree)
    spdx:Core/ProfileIdentifierType/core               ok
    spdx:Core/extension                                WRONG
  relative-ref-matches-term.json createdBy (rdflib, pyld agree)
    spdx:Core/Person                                   WRONG
3.1-dev:
  enum-value-matches-term.json profileConformance (rdflib, pyld agree)
    spdx:Core/ProfileIdentifierType/core               ok
    spdx:Core/extension                                WRONG
  relative-ref-matches-term.json createdBy (rdflib, pyld agree)
    spdx:Core/Person                                   WRONG
fixed:
  enum-value-matches-term.json profileConformance (rdflib, pyld agree)
    spdx:Core/ProfileIdentifierType/core               ok
    spdx:Core/ProfileIdentifierType/extension          ok
  relative-ref-matches-term.json createdBy (rdflib, pyld agree)
    https://example.org/doc/Person                     ok
```

The same documents and contexts give identical results with
Apache Jena 5.2.0 (Titanium JSON-LD 1.4.1, Java) and jsonld.js 8.3.3
(JavaScript): this is how JSON-LD 1.1 works, not a quirk of one library.

## Round trip with standard tools

Does a real pipeline produce such strings? [roundtrip.py](roundtrip.py)
starts from a valid SPDX 3.0.1 file,
[roundtrip-start.json](roundtrip-start.json) (absolute ids only), and uses
only standard steps:

1. `step1.json`: the start file. spdx3-validate: valid.
2. `step2.ttl`: read as RDF with rdflib, saved as Turtle (as any RDF store
   would keep it).
3. `step3.json`: written as JSON-LD again with pyld: from RDF, then compacted
   with the SPDX context and the base it is published at,
   `https://example.org/doc/`. jsonld.js gives the same output.
4. `step4.json`: a tool that edits the file as plain JSON (as the spec's
   "Parsing JSON-LD as JSON" section allows) adds an `Annotation` about the
   Person, copying its `spdxId` as written into `subject`.

```sh
venv/bin/pip install pyld spdx3-validate
venv/bin/python roundtrip.py   # writes roundtrip-out/<context>/step*.json
```

Output (2026-11-18):

```text
3.0.1:
  step1.json  valid SPDX 3 JSON (absolute ids)
              spdx3-validate: valid
  step2.ttl   RDF (Turtle)
  step3.json  JSON-LD again; same RDF as step1: True
              spdx3-validate: INVALID 'Person' does not match '^(?!_:).+:.+'
  step4.json  Annotation subject 'Person' -> spdx:Core/Person
fixed:
  step1.json  valid SPDX 3 JSON (absolute ids)
              spdx3-validate: not run
  step2.ttl   RDF (Turtle)
  step3.json  JSON-LD again; same RDF as step1: True
              spdx3-validate: not run
  step4.json  Annotation subject 'Person' -> https://example.org/doc/Person
```

`step3.json` with the published 3.0.1 context:

```json
{
  "@context": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
  "@graph": [
    {
      "spdxId": "_:n…",
      "type": "CreationInfo",
      "created": "2026-11-18T00:00:00Z",
      "createdBy": "https://example.org/doc/Person",
      "spdx:Core/specVersion": "3.0.1"
    },
    {
      "spdxId": "Person",
      "type": "Person",
      "creationInfo": "_:n…",
      "spdx:Core/name": "Jane Doe"
    }
  ]
}
```

What it shows:

- Step 3 is valid JSON-LD: its canonical RDF (URDNA2015) is identical to
  step 1. It is not valid SPDX 3 JSON.
- Standard producers write relative ids: `"spdxId": "Person"`.
- With the published context the same element is `"Person"` as an id but
  `"https://example.org/doc/Person"` as a reference: the context cannot
  express a relative reference, so the compactor avoids one. With the fixed
  context both are `"Person"`.
- Step 4: the copied `"Person"` becomes the class `Core/Person` with the
  published context, and the Person element with the fixed one.

## The fix

`fixed/spdx-context.jsonld` is built by bact/spec-parser `type-id-class`
from spdx/spdx-3-model 44542aa (develop 25267e7 fails earlier, on
`/Core/Modality`). The fix changes only the context generator:

- Class-valued terms: `"@type": "@vocab"` → `"@type": "@id"`. References
  resolve against the document base, as JSON-LD intends.
- Enumerations keep their scoped `@vocab`; entries that share a name with a
  top-level term are mapped explicitly in that scoped context. JSON-LD 1.1
  §4.1.11 lets property-scoped contexts override even `@protected` terms.
- The five spec individuals (`NoneElement`, `NoAssertionElement`,
  `SpdxOrganization`, `NoneLicense`, `NoAssertionLicense`) get no context
  term, so they are written as IRIs or compact IRIs:
  `spdx:Core/SpdxOrganization`, `spdx:ExpandedLicensing/NoneLicense`. This
  form is already schema-valid in 3.0.1. The bare names
  (`"SpdxOrganization"`) are not valid under the fixed context.

## Notes

- A document stays valid against the version its `@context` names; the 3.0.x
  contexts are frozen. Moving a document to 3.1 already changes every term
  IRI (`…/3.0.1/terms/…` to `…/3/terms/…`); rewriting bare individual names
  is one more mechanical step.
- Absolute IRIs, compact IRIs and blank nodes expand the same with `@vocab`
  and `@id`, so references that are valid today keep their meaning.
- Any string in an enumeration, including a typo, still expands into the
  SPDX namespace
  ([spdx/spdx-3-model#1167](https://github.com/spdx/spdx-3-model/issues/1167)
  point 2); not covered here.
- Step 3 also fails the SPDX JSON Schema for reasons this fix does not
  touch. Standard JSON-LD output differs from SPDX 3 JSON in three more ways:
  - the blank node id is written as `spdxId` (the alias of `@id`), but SPDX
    expects `@id` for blank nodes and `spdxId` only for IRIs;
  - a single value is written as a string (`"createdBy": "…"`), but the
    schema requires an array;
  - string properties are written as `spdx:Core/name`, not `name`: the
    context types them as `xsd:string`, but JSON-LD's from-RDF algorithm
    omits `xsd:string` (the RDF 1.1 default), so the `name` term no longer
    matches.

  So "SPDX 3 JSON is a strict subset of JSON-LD" means output from a standard
  JSON-LD producer is usually not valid SPDX 3 JSON, even when the data is.
