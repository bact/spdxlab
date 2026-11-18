# SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: CC0-1.0

"""Round-trip a valid SPDX 3 JSON file through RDF with standard tools; write each step to roundtrip-out/.

usage: python roundtrip.py [NAME=CONTEXT ...]   (needs: pip install rdflib pyld; spdx3-validate optional)
CONTEXT: URL or path of spdx-context.jsonld; defaults to published 3.0.1 and fixed/spdx-context.jsonld.
"""

import json
import os
import shlex
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from pyld import jsonld
from rdflib import Graph

HERE = Path(__file__).parent
OUT = HERE / "roundtrip-out"
CONTEXTS = {
    "3.0.1": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
    "fixed": str(HERE / "fixed" / "spdx-context.jsonld"),
}
BASE = "https://example.org/doc/"  # where the file is published
START = json.loads((HERE / "roundtrip-start.json").read_text())


def load(src):
    if src.startswith("https://"):
        with urllib.request.urlopen(src) as r:
            return json.load(r)
    with open(src) as f:
        return json.load(f)


def with_ctx(doc, ctx):
    return {**doc, "@context": ctx["@context"]}


def canon(doc, ctx):
    return jsonld.normalize(with_ctx(doc, ctx), {"algorithm": "URDNA2015", "format": "application/n-quads", "base": BASE})


def validate(path, name):
    # spdx3-validate knows the published 3.0.x contexts only
    if name != "3.0.1":
        return "not run"
    cmd = shlex.split(os.environ.get("SPDX3_VALIDATE", "spdx3-validate"))
    if not shutil.which(cmd[0]):
        return "not run"
    r = subprocess.run([*cmd, "-q", "-j", str(path)], capture_output=True, text=True, check=False)
    first = next((ln.split(": ", 1)[1] for ln in (r.stdout + r.stderr).splitlines() if "does not match" in ln), "")
    return "valid" if r.returncode == 0 else f"INVALID {first}"


def created_by(doc, ctx, prop):
    nq = jsonld.to_rdf(with_ctx(doc, ctx), {"format": "application/n-quads", "base": BASE})
    return [ln.split(" ")[2] for ln in nq.splitlines() if f"/{prop}> " in ln]


OUT.mkdir(exist_ok=True)
srcs = dict(a.split("=", 1) for a in sys.argv[1:]) or CONTEXTS
for name, src in srcs.items():
    ctx = load(src)
    d = OUT / name
    d.mkdir(exist_ok=True)
    print(f"{name}:")

    # step 1: valid SPDX 3 JSON (absolute ids)
    (d / "step1.json").write_text(json.dumps(START, indent=2))
    print("  step1.json  valid SPDX 3 JSON (absolute ids)")
    print(f"              spdx3-validate: {validate(d / 'step1.json', name)}")

    # step 2: read as RDF, save as Turtle
    g = Graph().parse(data=json.dumps(with_ctx(START, ctx)), format="json-ld")
    g.serialize(d / "step2.ttl", format="turtle")
    print("  step2.ttl   RDF (Turtle)")

    # step 3: write JSON-LD again: from RDF, compact with the SPDX context and the publishing base
    nq = Graph().parse(d / "step2.ttl").serialize(format="nt")
    step3 = jsonld.compact(jsonld.from_rdf(nq, {"format": "application/n-quads"}), ctx, {"base": BASE})
    step3["@context"] = START["@context"]
    (d / "step3.json").write_text(json.dumps(step3, indent=2))
    same = canon(step3, ctx) == canon(START, ctx)
    print(f"  step3.json  JSON-LD again; same RDF as step1: {same}")
    print(f"              spdx3-validate: {validate(d / 'step3.json', name)}")

    # step 4: a plain JSON tool adds an Annotation about the Person, copying its spdxId as written
    person = next(n for n in step3["@graph"] if n.get("type") == "Person")
    ci = person["creationInfo"]
    step4 = json.loads(json.dumps(step3))
    step4["@graph"].append(
        {
            "type": "Annotation",
            "spdxId": BASE + "Annotation1",
            "creationInfo": ci,
            "annotationType": "review",
            "subject": person["spdxId"],
            "statement": "Reviewed",
        }
    )
    (d / "step4.json").write_text(json.dumps(step4, indent=2))
    subject = created_by(step4, ctx, "subject")[0].strip("<>").replace(ctx["@context"]["spdx"], "spdx:")
    print(f"  step4.json  Annotation subject {person['spdxId']!r} -> {subject}")
