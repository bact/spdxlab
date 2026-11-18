# SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: CC0-1.0

"""Read example.json with a JSON-LD context and show what createdBy points to.

usage: python quick.py [NAME=CONTEXT ...]   (needs: pip install rdflib)
CONTEXT: URL or path of spdx-context.jsonld; defaults to the published 3.0.1 and 3.1-dev ones.
Each context is used as published, then with class-valued terms typed "@id"
(https://github.com/spdx/spec-parser/pull/205).
"""

import json
import sys
import urllib.request
from pathlib import Path

from rdflib import RDF, Graph

URLS = {
    "3.0.1": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
    "3.1-dev": "https://spdx.github.io/spdx-spec/v3.1-dev/rdf/spdx-context.jsonld",
}
BASE = "https://example.org/doc/"
EXAMPLE = json.loads((Path(__file__).parent / "example.json").read_text())


def load(src):
    if src.startswith("https://"):
        with urllib.request.urlopen(src) as r:
            return json.load(r)["@context"]
    with open(src) as f:
        return json.load(f)["@context"]


def class_valued(ctx):
    # "@type": "@vocab" without a scoped @context = range is a class, not an enumeration
    return [k for k, v in ctx.items() if isinstance(v, dict) and v.get("@type") == "@vocab" and "@context" not in v]


def with_id(ctx):
    terms = class_valued(ctx)
    return {k: ({"@id": v["@id"], "@type": "@id"} if k in terms else v) for k, v in ctx.items()}


def show(label, ctx):
    # example.json as is, with its @context replaced by ctx
    g = Graph().parse(data=json.dumps({**EXAMPLE, "@context": ctx}), format="json-ld", base=BASE)
    person = next(s for s, o in g.subject_objects(RDF.type) if str(o).endswith("/Core/Person"))
    created_by = next(o for s, p, o in g if str(p).endswith("/Core/createdBy"))
    print(f"   {label:13} {created_by!s:45} {'ok' if created_by == person else 'WRONG'}")


srcs = dict(a.split("=", 1) for a in sys.argv[1:]) or URLS
for name, src in srcs.items():
    ctx = load(src)
    print(f"{name}: {len(class_valued(ctx))} class-valued terms typed @vocab; createdBy ->")
    show("as published", ctx)
    show("with @id", with_id(ctx))
