# SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
# SPDX-License-Identifier: CC0-1.0
"""Copy shapes as N-Triples for Jena, declaring rdf: and rdfs: in SPARQL queries that use them undeclared.

Usage: python prepare.py SHAPES.ttl OUT.nt [--no-sparql]
"""

import sys

from rdflib import Graph, Literal
from rdflib.namespace import SH

PREFIXES = "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"


def main():
    g = Graph().parse(sys.argv[1])
    if "--no-sparql" in sys.argv:
        g.remove((None, SH.sparql, None))
    for s, q in list(g.subject_objects(SH.select)):
        if "rdf:" in q and "PREFIX rdf:" not in q:
            g.set((s, SH.select, Literal(PREFIXES + q)))
    g.serialize(sys.argv[2], format="nt", encoding="utf-8")


if __name__ == "__main__":
    main()
