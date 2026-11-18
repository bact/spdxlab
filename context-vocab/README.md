---
SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
SPDX-FileType: DOCUMENTATION
SPDX-License-Identifier: CC0-1.0
---

# SPDX 3: JSON-LD context makes standard processors misread strings

Reproduction for
[spdx/spdx-3-model#1477](https://github.com/spdx/spdx-3-model/issues/1477),
[spdx/spdx-3-model#1167](https://github.com/spdx/spdx-3-model/issues/1167)
(point 1) and
[spdx/spec-parser#204](https://github.com/spdx/spec-parser/issues/204).
Fix: bact/spec-parser branch
[`type-id-class`](https://github.com/bact/spec-parser/tree/type-id-class).

## In short

- The spec says SPDX 3 JSON can be parsed with standard JSON-LD libraries:
  rdflib, pyld (Python), Apache Jena (Java), jsonld.js (JavaScript).
- With the published context, they misread some strings, because a string
  is first matched against the context's top-level terms.
- Two cases:
  1. **Enumeration value** named like a term: `"extension"` in
     `profileConformance` becomes the property `Core/extension`. Affects
     schema-valid documents.
  2. **Relative reference** named like a term: `"Person"` in `createdBy`
     becomes the class `Core/Person`, not the element `<base>Person`.
     Schema-invalid, but valid JSON-LD that standard tools write.
- All four libraries agree, so this is how JSON-LD 1.1 works, not a bug in
  one library. The fix is in the context generator.

## Files

| File | What it is |
| --- | --- |
| [enum-value-matches-term.json](enum-value-matches-term.json) | Case 1: valid SPDX 3.0.1 document with `profileConformance: ["core", "extension"]` |
| [relative-ref-matches-term.json](relative-ref-matches-term.json) | Case 2: `createdBy: ["Person"]` pointing to the element with `spdxId: "Person"` |
| [valid-absolute-ids.json](valid-absolute-ids.json) | Valid SPDX 3.0.1 document, start of the round trip |
| [fixed/spdx-context.jsonld](fixed/spdx-context.jsonld) | Context built by `type-id-class` from spdx/spdx-3-model 44542aa |
| [quick.py](quick.py) | Expands cases 1 and 2 with each context |
| [roundtrip.py](roundtrip.py) | Round trip through standard tools |

All examples use base `https://example.org/doc/`.

## 1. Expand the examples (seconds)

```sh
cd context-vocab
python3 -m venv venv && venv/bin/pip install rdflib pyld spdx3-validate
venv/bin/python quick.py                  # published 3.0.1, 3.1-dev, fixed
venv/bin/python quick.py NAME=CONTEXT ... # other contexts
```

`quick.py` reads each example unchanged except for its `@context`, and
prints what the strings expand to with rdflib and pyld (`spdx:` = the terms
namespace of that context).

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

- Same results with Apache Jena 5.2.0 (JSON-LD 1.1 via Titanium 1.4.1) and
  jsonld.js 8.3.3.
- spdx3-validate 0.0.7 on `enum-value-matches-term.json`: passes the JSON
  Schema, fails SHACL (`Core/extension` is not a `ProfileIdentifierType`).
- `relative-ref-matches-term.json` fails the JSON Schema on purpose (ids must
  be absolute IRIs or blank nodes). SHACL cannot see this: `spdxId` is an
  alias of `@id`, resolved before the RDF graph exists.

## 2. Round trip through standard tools

Do real tools write relative references? `roundtrip.py` starts from a valid
file and uses only standard steps:

1. `step1.json`: `valid-absolute-ids.json`.
2. `step2.ttl`: read as RDF with rdflib, saved as Turtle.
3. `step3.json`: written as JSON-LD again with pyld (from RDF, then compact
   with the SPDX context and the publishing base). jsonld.js gives the same.
4. `step4.json`: a plain JSON tool adds an `Annotation` whose `subject` is the
   Person's `spdxId` as written.

```sh
venv/bin/python roundtrip.py   # writes roundtrip-out/<context>/step*.json
```

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
  step2.ttl   RDF (Turtle)
  step3.json  JSON-LD again; same RDF as step1: True
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

- Step 3 is the same RDF (canonical URDNA2015) but no longer valid SPDX 3
  JSON: standard producers write relative ids (`"spdxId": "Person"`).
- The published context cannot express a relative reference, so the same
  element is `"Person"` as an id but an absolute IRI as a reference. With the
  fixed context both are `"Person"`.
- Step 4: the copied `"Person"` becomes the class `Core/Person` with the
  published context, and the element with the fixed one.

## The fix

bact/spec-parser `type-id-class` changes only the context generator:

- Class-valued terms: `"@type": "@vocab"` → `"@type": "@id"`.
- Enumeration entries that share a name with a top-level term: mapped
  explicitly in the scoped context. JSON-LD 1.1 §4.1.11 allows this even for
  `@protected` terms.
- The five spec individuals get no context term. Write
  `spdx:Core/SpdxOrganization`, not `SpdxOrganization` (already schema-valid
  in 3.0.1). Their IRIs do not change.

## Notes

- 3.0.x contexts are frozen; 3.0.x documents stay valid. Moving to 3.1
  already changes every term IRI; rewriting bare individual names is one
  more step.
- Absolute IRIs, compact IRIs and blank nodes expand the same with `@vocab`
  and `@id`.
- Not covered: any enumeration string, including a typo, still expands into
  the SPDX namespace
  ([spdx/spdx-3-model#1167](https://github.com/spdx/spdx-3-model/issues/1167)
  point 2).
- Step 3 also fails the schema for reasons outside this fix:
  - the blank node id is written as `spdxId`, not `@id`;
  - a single value is a string, not an array;
  - string properties become `spdx:Core/name`: the context types them
    `xsd:string`, which JSON-LD's from-RDF algorithm omits, so the `name`
    term no longer matches.
