# SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: CC0-1.0

"""Class-valued properties typed @vocab in the SPDX 3 JSON-LD context.

usage: python quick.py [NAME=CONTEXT ...]   (needs: pip install rdflib)
CONTEXT: URL or path of spdx-context.jsonld; defaults to the published 3.0.1 and 3.1-dev ones.
Each context is also checked with class-valued terms switched to "@type": "@id" (spec-parser#205).
"""

import json
import sys
import urllib.request

from rdflib import Graph

URLS = {
    "3.0.1": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
    "3.1-dev": "https://spdx.github.io/spdx-spec/v3.1-dev/rdf/spdx-context.jsonld",
}
BASE = "https://example.org/doc/"
# an element id that is also a context term name
DOC = {"@id": "_:ci", "type": "CreationInfo", "createdBy": ["Tool", "https://example.org/agent/1"]}


def load(src):
    if src.startswith("https://"):
        with urllib.request.urlopen(src) as r:
            return json.load(r)["@context"]
    with open(src) as f:
        return json.load(f)["@context"]


def class_valued(ctx):
    # "@type": "@vocab" without a scoped @vocab = range is a class, not an enumeration
    return sorted(k for k, v in ctx.items() if isinstance(v, dict) and v.get("@type") == "@vocab" and "@context" not in v)


def fixed(ctx):
    return {k: ({"@id": v["@id"], "@type": "@id"} if k in class_valued(ctx) else v) for k, v in ctx.items()}


def created_by(ctx):
    key = next(k for k in ctx if k == "createdBy" or k.endswith("_createdBy"))
    g = Graph().parse(data=json.dumps({"@context": ctx, **DOC}), format="json-ld", base=BASE)
    return key, sorted(str(o) for s, p, o in g if str(p).endswith("/createdBy"))


srcs = dict(a.split("=", 1) for a in sys.argv[1:]) or URLS
for name, src in srcs.items():
    ctx = load(src)
    terms = class_valued(ctx)
    print(f"{name}: {len(terms)} class-valued terms typed @vocab")
    for label, c in (("as published", ctx), ("with @id", fixed(ctx))):
        key, values = created_by(c)
        tool = next(v for v in values if v.endswith("/Tool"))
        print(f"   {label:13} {key} \"Tool\" -> {tool}")
