# SPDX-FileCopyrightText: 2026 SPDX contributors
# SPDX-License-Identifier: Apache-2.0

"""Merge issue, shown with published files only: SPDX 3.0.1 + 3.1-RC1 ontologies.

usage: python quick.py [FIXED_TTL]   (needs: pip install rdflib pyshacl)
FIXED_TTL: optional ontology built with the fix, to show the same merge passing.
"""

import re
import sys
import urllib.request

from pyshacl import validate
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS

URLS = {"3.0.1": "https://spdx.org/rdf/3.0.1/spdx-model.ttl", "3.1-RC1": "https://spdx.org/rdf/3.1/spdx-model.ttl"}
CORE = "https://spdx.org/rdf/3/terms/Core/"
CREATION_INFO, CI_CLASS = URIRef(CORE + "creationInfo"), URIRef(CORE + "CreationInfo")
TERMS = re.compile(r"^https://spdx\.org/rdf/3\.[0-9.]+/terms/")


def load(src):
    # versioned term IRIs (3.0.1/terms/, 3.1/terms/) -> one canonical form, as proposed for SPDX 3.1
    if src.startswith("https://"):
        with urllib.request.urlopen(src) as r:
            src = r.read()
        g = Graph().parse(data=src, format="turtle")
    else:
        g = Graph().parse(src)
    out = Graph()
    for t in g:
        out.add(tuple(URIRef(TERMS.sub("https://spdx.org/rdf/3/terms/", x)) if isinstance(x, URIRef) else x for x in t))
    return out


def individuals(g):
    # spec-defined individuals and their CreationInfo records only
    data = Graph()
    for s in set(g.subjects(CREATION_INFO, None)) | set(g.subjects(RDF.type, CI_CLASS)):
        for p, o in g.predicate_objects(s):
            data.add((s, p, o))
    return data


def creation_info_violations(data, shapes):
    # add the class hierarchy so Element's shape applies to subclasses
    data = data + Graph()
    for t in shapes.triples((None, RDFS.subClassOf, None)):
        data.add(t)
    _, _, text = validate(data, shacl_graph=shapes, inference="none")
    return [b for b in text.split("Constraint Violation")[1:] if f"Result Path: <{CREATION_INFO}>" in b]


if len(sys.argv) > 1:
    URLS["fixed"] = sys.argv[1]
g = {v: load(u) for v, u in URLS.items()}
shapes = g["3.1-RC1"]

print("1. NoneElement's CreationInfo, as published")
for v, graph in g.items():
    ci = graph.value(URIRef(CORE + "NoneElement"), CREATION_INFO)
    print(f"   {v:8} {ci}  specVersion={graph.value(ci, URIRef(CORE + 'specVersion'))}  created={graph.value(ci, URIRef(CORE + 'created'))}")

merged = individuals(g["3.0.1"]) + individuals(g["3.1-RC1"])
print("\n2. Merged: creationInfo values per individual (Element.creationInfo allows exactly 1)")
for ind in sorted(set(merged.subjects(CREATION_INFO, None))):
    cis = sorted(str(c).rsplit("/", 2)[-2] for c in merged.objects(ind, CREATION_INFO))
    print(f"   {str(ind).rsplit('/', 1)[-1]:20} {len(cis)}  ({', '.join(cis)})")

print("\n3. SHACL violations on creationInfo (shapes from 3.1-RC1)")
cases = [("3.0.1 alone", individuals(g["3.0.1"])), ("3.1-RC1 alone", individuals(g["3.1-RC1"])), ("3.0.1 + 3.1-RC1", merged)]
if "fixed" in g:
    cases.append(("3.0.1 + fixed", individuals(g["3.0.1"]) + individuals(g["fixed"])))
for label, data in cases:
    v = creation_info_violations(data, shapes)
    msg = re.search(r"Message: (.*)", v[0]).group(1) if v else ""
    print(f"   {label:16} {len(v)}  {msg}")
