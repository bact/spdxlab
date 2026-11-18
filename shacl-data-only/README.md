---
SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
SPDX-FileType: DOCUMENTATION
SPDX-License-Identifier: CC0-1.0
---

# SPDX 3: SHACL shapes need the ontology in the data graph

Shows why SPDX 3 SHACL validation needs the class hierarchy merged into
the data, and compares ways to remove that need.
Builds on
[spdx/spec-parser#221](https://github.com/spdx/spec-parser/pull/221).
Fix: [bact/spec-parser#22](https://github.com/bact/spec-parser/pull/22)
(branch `class-check-data-only`).

## In short

- SHACL follows `rdfs:subClassOf` **in the data graph** for both
  `sh:targetClass` and `sh:class`
  ([SHACL §2.1.3.3](https://www.w3.org/TR/shacl/#targetClass),
  [§4.1.1](https://www.w3.org/TR/shacl/#ClassConstraintComponent)).
- SPDX documents do not contain the hierarchy. It is only in the ontology.
- With the data alone, the published shapes:
  - miss errors: a `Package` without `creationInfo` is not checked, because
    the shape that requires it targets `Element`;
  - report false errors: a `Person` in `createdBy` fails `sh:class Agent`.
- The workaround is to merge the ontology into the data graph. Validators
  that do not, or that cannot (Jena reads one data graph), get wrong results.
- [spdx/spec-parser#221](https://github.com/spdx/spec-parser/pull/221) makes
  every class a `sh:NodeShape`. That lets Jena find the shapes, but does not
  remove the need for the ontology.
- Recommended fix (variant 5): list the subclasses in the shapes, and check
  class-valued properties with one shared `sh:in` on `rdf:type` per range
  class. Same results with and without the ontology, at about the same speed
  as today.

## Files

| File | What it is |
| --- | --- |
| [subclass-instances.ttl](subclass-instances.ttl) | Valid elements of subclasses (`Person`, `Package`, `File`, `Relationship`, `Hash`), and one `Package` without `creationInfo`. Expected: 1 result |
| [wrong-reference-type.ttl](wrong-reference-type.ttl) | A `Relationship` whose `to` is a `CreationInfo`, not an `Element`. Expected: 1 result |
| [sparql-subclass.ttl](sparql-subclass.ttl) | Valid `SupportRelationship`. Its SPARQL constraints use `rdfs:subClassOf*`. Expected: no results |
| [variants.py](variants.py) | Builds the shape variants from a published `spdx-model.ttl` |
| [validate.py](validate.py) | Validates each test file with each variant, with pySHACL |
| [fixed/spdx-model.ttl](fixed/spdx-model.ttl) | Built by `class-check-data-only` from spdx/spdx-3-model 44542aa |
| [bench-data.py](bench-data.py) | Writes a large document for timing |
| [jena/](jena/) | Jena timing harness |

## Shape variants

| Variant | Targets | Class-valued properties | Triples |
| --- | --- | --- | ---: |
| 0-published | none: relies on implicit class targets; some classes not typed `sh:NodeShape` | `sh:class X` | 6,505 |
| 1-pr221 | spdx/spec-parser#221: `sh:NodeShape`, `sh:targetClass` itself | `sh:class X` | 6,754 |
| 2-inline-or | itself and all subclasses | `sh:or ([sh:class X] [sh:class Sub1] ...)` on each property | 11,127 |
| 3-shared-or | itself and all subclasses | same `sh:or`, one shared shape per class, used with `sh:node` | 7,838 |
| 4-node-inherit | itself; each shape `sh:node` its parent | as 3 | 7,639 |
| 5-shared-type-in | itself and all subclasses | one shared shape per class: at least one `rdf:type` `sh:in (X Sub1 ...)`, used with `sh:node` | 7,643 |
| fixed | as 5, built by spec-parser | as 5 | 8,513 |

- 2 to 5 also drop `sh:class` on enumeration properties: `sh:in` already
  lists the entries, and `sh:class` needs their types in the data.
- `sh:class` stays where the class has no subclasses.
- `fixed` is built from a newer model than the published file, so it has
  more triples.

## 1. Results

```sh
cd shacl-data-only
python3 -m venv venv && venv/bin/pip install rdflib pyshacl
venv/bin/python variants.py PATH/TO/spdx-model.ttl   # default: published 3.1-dev
venv/bin/python validate.py
```

"+ ontology" adds the `rdfs:subClassOf` triples and the types of the
enumeration entries to the data. pySHACL 0.40.2, `inference="none"`.
Each line: focus node, path, constraint component.

```text
0-published:
  subclass-instances.ttl   data only    (bnode) algorithm Class; (bnode) createdBy Class; Rel from Class; Rel relationshipType Class; Rel to Class
  subclass-instances.ttl   + ontology   BadPkg creationInfo MinCount
  wrong-reference-type.ttl data only    BadRel from Class; BadRel relationshipType Class; BadRel to Class; ci createdBy Class
  wrong-reference-type.ttl + ontology   BadRel to Class
  sparql-subclass.ttl      data only    (bnode) createdBy Class; Support supportLevel Class
  sparql-subclass.ttl      + ontology   (no results)
1-pr221:
  subclass-instances.ttl   data only    (bnode) algorithm Class; (bnode) createdBy Class; Rel from Class; Rel relationshipType Class; Rel to Class
  subclass-instances.ttl   + ontology   BadPkg creationInfo MinCount
  wrong-reference-type.ttl data only    BadRel from Class; BadRel relationshipType Class; BadRel to Class; ci createdBy Class
  wrong-reference-type.ttl + ontology   BadRel to Class
  sparql-subclass.ttl      data only    (bnode) createdBy Class; Support supportLevel Class
  sparql-subclass.ttl      + ontology   (no results)
2-inline-or:
  subclass-instances.ttl   data only    BadPkg creationInfo MinCount
  subclass-instances.ttl   + ontology   BadPkg creationInfo MinCount
  wrong-reference-type.ttl data only    BadRel to Or
  wrong-reference-type.ttl + ontology   BadRel to Or
  sparql-subclass.ttl      data only    Support SPARQL
  sparql-subclass.ttl      + ontology   (no results)
3-shared-or:
  subclass-instances.ttl   data only    BadPkg creationInfo MinCount
  subclass-instances.ttl   + ontology   BadPkg creationInfo MinCount
  wrong-reference-type.ttl data only    BadRel to Node
  wrong-reference-type.ttl + ontology   BadRel to Node
  sparql-subclass.ttl      data only    Support SPARQL
  sparql-subclass.ttl      + ontology   (no results)
4-node-inherit:
  subclass-instances.ttl   data only    BadPkg Node
  subclass-instances.ttl   + ontology   BadPkg Node; BadPkg creationInfo MinCount
  wrong-reference-type.ttl data only    BadRel to Node
  wrong-reference-type.ttl + ontology   BadRel to Node
  sparql-subclass.ttl      data only    Support Node
  sparql-subclass.ttl      + ontology   (no results)
5-shared-type-in:
  subclass-instances.ttl   data only    BadPkg creationInfo MinCount
  subclass-instances.ttl   + ontology   BadPkg creationInfo MinCount
  wrong-reference-type.ttl data only    BadRel to Node
  wrong-reference-type.ttl + ontology   BadRel to Node
  sparql-subclass.ttl      data only    Support SPARQL
  sparql-subclass.ttl      + ontology   (no results)
fixed (spec-parser):
  subclass-instances.ttl   data only    BadPkg creationInfo MinCount
  subclass-instances.ttl   + ontology   BadPkg creationInfo MinCount
  wrong-reference-type.ttl data only    BadRel to Node
  wrong-reference-type.ttl + ontology   BadRel to Node
  sparql-subclass.ttl      data only    Support SPARQL
  sparql-subclass.ttl      + ontology   (no results)
```

- Jena 5.2.0, data only, gives the same results for 2 to 5 and fixed.
- 0 and 1 are right only with the ontology. pySHACL treats an `owl:Class`
  shape as a class target, so 0 and 1 give the same results here.
- 2, 3, 5 and fixed are right with and without the ontology, except for
  `sparql-subclass.ttl` (see below).
- 4 gives right answers but worse messages: the `Package` error is reported
  as "does not conform to `Element`" (`Node`), not as the missing property.
  With the ontology, the same error is reported twice.

## 2. Timing

```sh
venv/bin/python bench-data.py 20000 big.ttl   # 60k elements, 20 bad packages
cat big.ttl PATH/TO/spdx-model.ttl > big-merged.ttl
venv/bin/python jena/prepare.py variants/5-shared-type-in.ttl v5.nt --no-sparql
# Jena jars in jena/lib (mvn dependency:copy-dependencies of org.apache.jena:jena-shacl:5.2.0)
java -cp "jena/lib/*" jena/Bench.java v5.nt big.ttl
```

Apache Jena 5.2.0, best of 3 runs, 60,001 elements.
"merged" adds the whole published ontology to the data.
Shapes go through [jena/prepare.py](jena/prepare.py) first (see notes).

SPARQL constraints removed, to compare the class checks alone.

| Variant | Data only | Merged |
| --- | ---: | ---: |
| 0-published | 0 results | 0 results |
| 1-pr221 | 1.49 s, **80,001 results** | 1.39 s, 20 results |
| 2-inline-or | 25.57 s, 20 | 3.55 s, 20 |
| 3-shared-or | 25.43 s, 20 | 3.20 s, 20 |
| 4-node-inherit | 22.07 s, 20 | 5.32 s, **80** |
| 5-shared-type-in | **1.40 s, 20** | 1.59 s, 20 |
| fixed | **1.58 s, 20** | 1.74 s, 20 |

- Expected: 20 results, one per bad package.
- 1 data only: 80,001 false results, from `sh:class` on subclasses.
- 2 and 3 are slow without the ontology: the `sh:or` runs many `sh:class`
  alternatives for each value.
- 4 reports each bad package 4 times when merged.
- With the 73 SPARQL constraints kept: 1-pr221 26.15 s and 24.60 s, fixed
  23.41 s (data only). They cost more than all the core constraints
  together.

## 3. Still needs the ontology: SPARQL constraints

- 47 of the 73 SPARQL constraints (from `RelationshipType.md`) check the
  class of `from` and `to` with `?x rdf:type/rdfs:subClassOf* <Class>`.
- Without the ontology, `subClassOf*` matches only the direct type, so a
  `Package` is not an `Artifact`: `sparql-subclass.ttl` gets a false error
  with variants 2 to 5 and fixed. 0 and 1 do not report it only because they
  do not check the `SupportRelationship` at all.
- Fix belongs in the model, for example
  `?x rdf:type ?t . VALUES ?t { <Core/Artifact> <Software/Package> ... }`,
  or in the generator by expanding the class list.

## Notes

- **Jena cannot load the published 3.1-dev `spdx-model.ttl`.** The SPARQL
  queries (71 of 73) use `rdf:` and `rdfs:` without declaring them
  (no `PREFIX`, no `sh:prefixes`; SHACL §5.2.1). Jena 5.2.0 stops with
  "Unresolved prefixed name: rdf:type". pySHACL accepts them.
  [jena/prepare.py](jena/prepare.py) adds the two `PREFIX` lines.
- Variant 0 has no `sh:targetClass`. Implicit class targets need the shape
  to be an `rdfs:Class` and a `sh:NodeShape`; the classes are `owl:Class`
  only, and some are not `sh:NodeShape`. So Jena checks nothing (0 results).
  That is what
  [spdx/spec-parser#221](https://github.com/spdx/spec-parser/pull/221) fixes.
- Why `sh:in` on `rdf:type` and not `sh:or` of `sh:class`: `sh:in` is one
  set lookup per value. `sh:or` runs up to 116 `sh:class` checks
  (`Element` has 115 subclasses), each walking `rdfs:subClassOf` in the data.
- Variant 5 still works when RDFS inference adds the superclass types:
  any one matching `rdf:type` is enough (`sh:qualifiedMinCount 1`).
- Shared shapes in 3, 4 and 5 have IRIs (`urn:spdxlab:shape:...`) only
  because rdflib 7.6 writes some shared blank nodes wrongly to Turtle. The
  spec-parser fix uses blank nodes; its output reads back unchanged.
