# SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
# SPDX-License-Identifier: CC0-1.0
"""Build SHACL shape variants from an SPDX 3 spdx-model.ttl.

Usage: python variants.py [MODEL]   (default: published 3.1-dev)
Writes variants/<name>.ttl.
"""

import sys
from pathlib import Path

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SH

# Shared shapes get IRIs: rdflib 7.6 Turtle output loses some shared blank nodes
SHAPE = "urn:spdxlab:shape:"
PUBLISHED = "https://spdx.github.io/spdx-spec/v3.1-dev/rdf/spdx-model.ttl"


def subclasses(g, c):
    out, todo = set(), [c]
    while todo:
        for s in g.subjects(RDFS.subClassOf, todo.pop()):
            if s not in out:
                out.add(s)
                todo.append(s)
    return out


def classes(g):
    return set(g.subjects(RDF.type, OWL.Class))


# Steps


def target_self(g):
    """spdx/spec-parser#221: every class is a NodeShape targeting itself."""
    for c in classes(g):
        g.add((c, RDF.type, SH.NodeShape))
        g.add((c, SH.targetClass, c))


def target_subclasses(g):
    """Each class shape also targets all its subclasses."""
    for c in classes(g):
        for s in subclasses(g, c):
            g.add((c, SH.targetClass, s))


def node_inherit(g):
    """Alternative to target_subclasses: each class shape includes its parent."""
    for c in classes(g):
        for p in g.objects(c, RDFS.subClassOf):
            g.add((c, SH.node, p))


def drop_enum_class(g):
    """Enumerations: sh:in already lists the values; sh:class needs their type in the data."""
    for ps, cls in list(g.subject_objects(SH["class"])):
        if (ps, SH["in"], None) in g:
            g.remove((ps, SH["class"], cls))


def shape_iri(cls, kind):
    return URIRef(SHAPE + kind + ":" + str(cls).rsplit("/terms/", 1)[-1])


def class_checks(g):
    """(property shape, class) pairs whose class has subclasses."""
    return [(ps, c) for ps, c in g.subject_objects(SH["class"]) if subclasses(g, c)]


def or_list(g, cls):
    alts = []
    for x in sorted({cls} | subclasses(g, cls)):
        b = BNode()
        g.add((b, SH["class"], x))
        alts.append(b)
    return Collection(g, BNode(), alts).uri


def inline_or(g):
    """sh:class X -> sh:or ([sh:class X] [sh:class Sub1] ...), one list per property."""
    for ps, cls in class_checks(g):
        g.remove((ps, SH["class"], cls))
        g.add((ps, SH["or"], or_list(g, cls)))


def shared_or(g):
    """Same sh:or, but one shared shape per class, used through sh:node."""
    shared = {}
    for ps, cls in class_checks(g):
        if cls not in shared:
            shared[cls] = shape_iri(cls, "or")
            g.add((shared[cls], RDF.type, SH.NodeShape))
            g.add((shared[cls], SH["or"], or_list(g, cls)))
        g.remove((ps, SH["class"], cls))
        g.add((ps, SH.node, shared[cls]))


def shared_type_in(g):
    """One shared shape per class: at least one rdf:type is X or a subclass (sh:in)."""
    shared = {}
    for ps, cls in class_checks(g):
        if cls not in shared:
            n, p, q = shape_iri(cls, "type"), BNode(), BNode()
            g.add((n, RDF.type, SH.NodeShape))
            g.add((n, SH.property, p))
            g.add((p, SH.path, RDF.type))
            types = Collection(g, BNode(), sorted({cls} | subclasses(g, cls)))
            g.add((q, SH["in"], types.uri))
            g.add((p, SH.qualifiedValueShape, q))
            g.add((p, SH.qualifiedMinCount, Literal(1)))
            shared[cls] = n
        g.remove((ps, SH["class"], cls))
        g.add((ps, SH.node, shared[cls]))


VARIANTS = {
    "0-published": [],
    "1-pr221": [target_self],
    "2-inline-or": [target_self, target_subclasses, drop_enum_class, inline_or],
    "3-shared-or": [target_self, target_subclasses, drop_enum_class, shared_or],
    "4-node-inherit": [target_self, node_inherit, drop_enum_class, shared_or],
    "5-shared-type-in": [target_self, target_subclasses, drop_enum_class, shared_type_in],
}


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else PUBLISHED
    base = Graph().parse(src, format="turtle")
    out = Path(__file__).parent / "variants"
    out.mkdir(exist_ok=True)
    for name, steps in VARIANTS.items():
        g = Graph()
        for t in base:
            g.add(t)
        for step in steps:
            step(g)
        g.serialize(out / f"{name}.ttl", format="turtle")
        print(f"{name:18} {len(g):6} triples")


if __name__ == "__main__":
    main()
