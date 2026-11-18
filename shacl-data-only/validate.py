# SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
# SPDX-License-Identifier: CC0-1.0
"""Validate the test files with each shape variant, with and without the ontology in the data graph.

Usage: python validate.py   (run variants.py first)
"""

from pathlib import Path

from pyshacl import validate
from rdflib import Graph
from rdflib.namespace import OWL, RDF, RDFS, SH

HERE = Path(__file__).parent
DATA = ["subclass-instances.ttl", "wrong-reference-type.ttl", "sparql-subclass.ttl"]


def short(x):
    return str(x).rsplit("/", 1)[-1].rsplit("#", 1)[-1] if x is not None else ""


def results(report):
    out = set()
    for r in report.subjects(RDF.type, SH.ValidationResult):
        if (None, SH.detail, r) in report:
            continue
        focus = report.value(r, SH.focusNode)
        focus = short(focus) if not focus.startswith("_:") and "/" in focus else "(bnode)"
        path = short(report.value(r, SH.resultPath))
        comp = short(report.value(r, SH.sourceConstraintComponent)).removesuffix("ConstraintComponent")
        out.add(f"{focus} {path} {comp}".replace("  ", " "))
    return sorted(out)


def ontology(shapes):
    """The part of the ontology sh:class needs in the data graph: subclasses and individuals' types."""
    h = Graph()
    for c in shapes.subjects(RDF.type, OWL.Class):
        for p in shapes.objects(c, RDFS.subClassOf):
            h.add((c, RDFS.subClassOf, p))
    for i in shapes.subjects(RDF.type, OWL.NamedIndividual):
        for t in shapes.objects(i, RDF.type):
            if str(i).startswith(str(t) + "/"):  # enumeration entries only
                h.add((i, RDF.type, t))
    return h


def main():
    files = sorted((HERE / "variants").glob("*.ttl")) + [HERE / "fixed" / "spdx-model.ttl"]
    for f in files:
        shapes = Graph().parse(f)
        name = "fixed (spec-parser)" if f.parent.name == "fixed" else f.stem
        print(f"{name}:")
        for d in DATA:
            data = Graph().parse(HERE / d)
            for mode, g in (("data only", data), ("+ ontology", data + ontology(shapes))):
                _, report, _ = validate(g, shacl_graph=shapes, inference="none")
                print(f"  {d:24} {mode:12} {'; '.join(results(report)) or '(no results)'}")


if __name__ == "__main__":
    main()
