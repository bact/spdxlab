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
against the context's terms. An element id that is also a term name, such as
`"Tool"`, expands to the SPDX class IRI `…/Core/Tool` instead of being
resolved against the document base. With `"@type": "@id"` it resolves as an
IRI, as intended.

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

The test document, with base `https://example.org/doc/`:

```json
{"@id": "_:ci", "type": "CreationInfo", "createdBy": "Tool"}
```

`"Tool"` stands for an element whose id is `Tool`, relative to the base.

Output (contexts from spdx/spdx-spec `gh-pages`, 2026-11-18):

```text
3.0.1: 37 class-valued terms typed @vocab
   as published  createdBy "Tool" -> https://spdx.org/rdf/3.0.1/terms/Core/Tool
   with @id      createdBy "Tool" -> https://example.org/doc/Tool
3.1-dev: 93 class-valued terms typed @vocab
   as published  createdBy "Tool" -> https://spdx.org/rdf/3/terms/Core/Tool
   with @id      createdBy "Tool" -> https://example.org/doc/Tool
```

"with @id" is the same context with the class-valued terms switched to
`"@type": "@id"`, as
[spdx/spec-parser#205](https://github.com/spdx/spec-parser/pull/205)
generates. Absolute IRIs and relative ids that are not term names (e.g.
`"agent-1"`) resolve the same either way; only values that match a term
name change meaning.

## Notes

- A term is counted as class-valued when it has `"@type": "@vocab"` and no
  scoped `@context`. In 3.1-dev all 93 have a class range in
  `spdx-model.ttl`; none is an enumeration.
- Enumerations keep `@vocab`. Their own issue (any string, including a typo,
  expands into the SPDX namespace) is
  [spdx/spdx-3-model#1167](https://github.com/spdx/spdx-3-model/issues/1167)
  point 2 and is not covered here.
