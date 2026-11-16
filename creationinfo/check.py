# SPDX-FileCopyrightText: 2026 SPDX contributors
# SPDX-License-Identifier: Apache-2.0

"""Reproduce the issues caused by mutable CreationInfo of spec-defined individuals.

usage: python check.py WORKDIR   (after build.sh WORKDIR)
"""
import subprocess
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, URIRef
from rdflib.namespace import RDF

W = Path(sys.argv[1])
LEGACY, CANON = "https://spdx.org/rdf/3.0.1/terms/", "https://spdx.org/rdf/3/terms/"
CI_TYPE = URIRef(CANON + "Core/CreationInfo")
P = {k: URIRef(CANON + "Core/" + k) for k in ("creationInfo", "specVersion", "created")}
NAMES = ["NoAssertionElement", "NoAssertionLicense", "NoneElement", "NoneLicense", "SpdxOrganization"]


def load(name):
    return Graph().parse(W / f"{name}.ttl")


def rewrite(g):
    # legacy rule: 3.0.1 term IRIs -> canonical term IRIs; nothing else
    out = Graph()
    for t in g:
        out.add(tuple(URIRef(CANON + x[len(LEGACY):]) if isinstance(x, URIRef) and str(x).startswith(LEGACY) else x for x in t))
    return out


def creation_infos(g):
    return {s: (sorted(map(str, g.objects(s, P["specVersion"]))), sorted(map(str, g.objects(s, P["created"]))))
            for s in g.subjects(RDF.type, CI_TYPE)}


def individual(g, name):
    return next(s for s in g.subjects(P["creationInfo"], None) if str(s).endswith("/" + name))


def shacl(merged, shapes):
    # validate only the individuals and their CreationInfo against the newer shapes
    data = Graph()
    for s in set(merged.subjects(RDF.type, CI_TYPE)) | set(merged.subjects(P["creationInfo"], None)):
        for p, o in merged.predicate_objects(s):
            data.add((s, p, o))
    ok, _, text = validate(data, shacl_graph=shapes, ont_graph=shapes, inference="none")
    paths = sorted({ln.split("Path: ")[1].rsplit(":", 1)[-1].rsplit("/", 1)[-1].rstrip(">") for ln in text.splitlines() if "Path: " in ln})
    return ok, text.count("Constraint Violation"), paths


def show(title, before, after):
    print(f"\n== {title}\n   before: {before}\n   after:  {after}")


v301 = rewrite(load("301"))

# 1. merging the 3.0.1 ontology with the next one breaks Element.creationInfo maxCount 1
def issue1(name):
    new = load(name)
    m = v301 + new
    dup = sorted(str(s).rsplit("/", 1)[-1] for s in set(m.subjects(P["creationInfo"], None))
                 if len(set(m.objects(s, P["creationInfo"]))) > 1)
    ok, n, paths = shacl(m, new)
    return f"individuals with >1 creationInfo: {dup or 'none'}; SHACL conforms={ok}, violations={n} on {paths or '-'}"
show("1. Merge 3.0.1 + new ontology (after legacy term rewrite)", issue1("before"), issue1("after"))

# 2. same CreationInfo IRI with different values breaks CreationInfo.created maxCount 1
def issue2(a, b):
    m = load(a) + load(b)
    cb = URIRef(CANON + "Core/createdBy")
    bad = {str(s).rsplit("/", 1)[-1]: (*v, sorted(str(o).rsplit("/", 1)[-1] for o in m.objects(s, cb)))
           for s, v in creation_infos(m).items() if len(v[0]) > 1 or len(v[1]) > 1 or len(set(m.objects(s, cb))) > 1}
    ok, n, paths = shacl(m, load(b))
    return f"CreationInfo with >1 value: {bad or 'none'}; SHACL conforms={ok}, violations={n} on {paths or '-'}"
print("\n== 2. Two builds sharing a CreationInfo IRI but not its values (why values must be frozen)")
print(f"   same values:    {issue2('after', 'after')}")
print(f"   created edited: {issue2('after', 'after-edit')}")
print(f"   createdBy edited: {issue2('after', 'after-edit-by')}")

# 3. CreationInfo IRIs published in 3.0.1 disappear
def issue3(name):
    gone = sorted(str(s) for s in set(creation_infos(v301)) - set(creation_infos(load(name))))
    return f"3.0.1 CreationInfo IRIs missing: {len(gone)} {gone[:1] + (['...'] if len(gone) > 1 else [])}"
show("3. CreationInfo IRIs published in 3.0.1 still defined", issue3("before"), issue3("after"))

# 4. provenance of 3.0.1 individuals rewritten
def issue4(name):
    g = load(name)
    ci = next(g.objects(individual(g, "NoneElement"), P["creationInfo"]))
    return f"NoneElement -> {ci} specVersion={creation_infos(g)[ci][0]} created={creation_infos(g)[ci][1]}"
show("4. Recorded origin of NoneElement (first published in 3.0.1, 2024-11-22)", issue4("before"), issue4("after"))

# 5. a new individual cannot be told apart from 3.0.1 ones
def issue5(name):
    g = load(name)
    out = []
    for n in ("NoneElement", "RedactedElement"):
        ci = next(g.objects(individual(g, n), P["creationInfo"]))
        sv, cr = creation_infos(g)[ci]
        out.append(f"{n}: {sv[0]} {cr[0]}")
    return "; ".join(out)
show("5. 3.0.1 individual vs. one added in 3.1 (RedactedElement)", issue5("before-new"), issue5("after-new"))

# 6. the CI check from spdx/spdx-3-model#1488 on each build
script = W / "model-after/.github/scripts/check_creationinfo.py"
print("\n== 6. CI check (#1488): generated ontology vs. released 3.0.1")
for name in ("before", "after", "after-edit", "after-edit-by"):
    r = subprocess.run([sys.executable, script, W / f"{name}.ttl"], capture_output=True, text=True)
    errs = [ln for ln in r.stdout.splitlines() if ln.startswith("error:")]
    print(f"   {name:14} {'FAIL' if r.returncode else 'pass'}  {len(errs)} error(s)")
