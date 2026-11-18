---
SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
SPDX-FileType: DOCUMENTATION
SPDX-License-Identifier: CC0-1.0
---

# SPDX 3: class-valued properties typed `@vocab` in the JSON-LD context

Reproduction for
[spdx/spec-parser#204](https://github.com/spdx/spec-parser/issues/204) and
[spdx/spdx-3-model#1167](https://github.com/spdx/spdx-3-model/issues/1167)
(point 1), fixed by
[spdx/spec-parser#205](https://github.com/spdx/spec-parser/pull/205).

## The problem in one paragraph

The JSON-LD context gives every object property `"@type": "@vocab"`.
For enumerations that is intended: each has a scoped `@vocab`, so
`"algorithm": "sha256"` expands to `…/HashAlgorithm/sha256`.
For properties whose range is a class (`createdBy`, `from`, `to`, `element`,
…) it is wrong: with `@vocab` coercion, a string value is first matched
against the context's terms. A reference to an element whose id is also a
term name, such as `"Person"`, expands to the SPDX class IRI `…/Core/Person`
instead of the element. With `"@type": "@id"` it resolves against the
document base, as intended.

## The example document

[example.json](example.json) is a plain SPDX 3.0.1 JSON document:

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

`createdBy` refers to the `Person` element by its `spdxId`. Read with base
`https://example.org/doc/`, that element is `https://example.org/doc/Person`,
so `createdBy` should point there (`ok` below). Any JSON-LD processor shows
where it points instead; the script below is only a shortcut.

## See it with published files (seconds)

| Name | URL |
| --- | --- |
| 3.0.1 | <https://spdx.org/rdf/3.0.1/spdx-context.jsonld> |
| 3.1-dev | <https://spdx.github.io/spdx-spec/v3.1-dev/rdf/spdx-context.jsonld> |

```sh
cd context-vocab
python3 -m venv venv && venv/bin/pip install rdflib
venv/bin/python quick.py                 # published contexts
venv/bin/python quick.py NAME=CONTEXT ... # local or other contexts
```

`quick.py` reads `example.json` unchanged except for its `@context`, which
it replaces with each context, first as published, then with the
class-valued terms switched to `"@type": "@id"`, as
[spdx/spec-parser#205](https://github.com/spdx/spec-parser/pull/205)
generates.

Output (contexts from spdx/spdx-spec `gh-pages`, 2026-11-18):

```text
3.0.1: 37 class-valued terms typed @vocab; createdBy ->
   as published  https://spdx.org/rdf/3.0.1/terms/Core/Person  WRONG
   with @id      https://example.org/doc/Person                ok
3.1-dev: 93 class-valued terms typed @vocab; createdBy ->
   as published  https://spdx.org/rdf/3/terms/Core/Person      WRONG
   with @id      https://example.org/doc/Person                ok
```

Absolute IRIs, and relative ids that are not term names (e.g. `"agent-1"`),
resolve the same either way; only ids that match a term name change meaning.

## Validity

`example.json` is not a valid SPDX 3 document, on purpose. The SPDX 3 JSON
Schema allows only absolute IRIs (`^(?!_:).+:.+`) or blank nodes (`_:…`) as
`spdxId` and as references, so both `"Person"` strings fail it
(spdx3-validate 0.0.7, SPDX 3.0.1). With absolute IRIs the document is valid,
and `@vocab` and `@id` then give the same result.

It is still valid JSON-LD, and SPDX data is RDF: the spec allows any RDF
serialization, and says SPDX 3 JSON may be parsed with standard JSON-LD
libraries. A generic JSON-LD or RDF consumer reads such a document as shown
above. SHACL cannot catch the relative `spdxId`: `spdxId` is an alias of
`@id`, so it is resolved against the base before the RDF graph exists. Here
SHACL fails only because `createdBy` points to the class `…/Core/Person`,
which is not an `Agent`.

## Notes

- A term is counted as class-valued when it has `"@type": "@vocab"` and no
  scoped `@context`. In 3.1-dev all 93 have a class range in
  `spdx-model.ttl`; none is an enumeration.
- Enumerations keep `@vocab`. Their own issue (any string, including a typo,
  expands into the SPDX namespace) is
  [spdx/spdx-3-model#1167](https://github.com/spdx/spdx-3-model/issues/1167)
  point 2 and is not covered here.
