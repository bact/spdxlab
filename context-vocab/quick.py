# SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: CC0-1.0

"""Read the example SPDX 3 JSON files with each JSON-LD context and show what the strings expand to.

usage: python quick.py [NAME=CONTEXT ...]   (needs: pip install rdflib; pyld is also used if installed)
CONTEXT: URL or path of spdx-context.jsonld; defaults to published 3.0.1, published 3.1-dev
and fixed/spdx-context.jsonld (built from bact/spec-parser branch type-id-class).
"""

import json
import sys
import urllib.request
from pathlib import Path

from rdflib import Graph

HERE = Path(__file__).parent
CONTEXTS = {
    "3.0.1": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
    "3.1-dev": "https://spdx.github.io/spdx-spec/v3.1-dev/rdf/spdx-context.jsonld",
    "fixed": str(HERE / "fixed" / "spdx-context.jsonld"),
}
BASE = "https://example.org/doc/"
# file, property, expected IRI ending of each value
CASES = [
    ("example.json", "createdBy", ["doc/Person"]),
    ("example-enum.json", "profileConformance", ["ProfileIdentifierType/core", "ProfileIdentifierType/extension"]),
]


def load(src):
    if src.startswith("https://"):
        with urllib.request.urlopen(src) as r:
            return json.load(r)["@context"]
    with open(src) as f:
        return json.load(f)["@context"]


def short(iri, ctx):
    # spdx: = the terms namespace of the context in use
    return iri.replace(ctx["spdx"], "spdx:")


def rdflib_values(doc, prop):
    g = Graph().parse(data=json.dumps(doc), format="json-ld", base=BASE)
    return sorted(str(o) for _, p, o in g if str(p).endswith("/" + prop))


def pyld_values(doc, prop):
    from pyld import jsonld

    nq = jsonld.to_rdf(doc, {"format": "application/n-quads", "base": BASE})
    return sorted(line.split(" ")[2].strip("<>") for line in nq.splitlines() if f"/{prop}> " in line)


try:
    import pyld  # noqa: F401

    PROCESSORS = {"rdflib": rdflib_values, "pyld": pyld_values}
except ImportError:
    PROCESSORS = {"rdflib": rdflib_values}

srcs = dict(a.split("=", 1) for a in sys.argv[1:]) or CONTEXTS
for name, src in srcs.items():
    ctx = load(src)
    print(f"{name}:")
    for file, prop, expected in CASES:
        # the example as is, with its @context replaced by ctx
        doc = {**json.loads((HERE / file).read_text()), "@context": ctx}
        results = {p: f(doc, prop) for p, f in PROCESSORS.items()}
        values = next(iter(results.values()))
        agree = "agree" if all(r == values for r in results.values()) else "DISAGREE"
        print(f"  {file} {prop} ({', '.join(results)} {agree})")
        for v in values:
            ok = "ok" if any(v.endswith(e) for e in expected) else "WRONG"
            print(f"    {short(v, ctx):50} {ok}")
