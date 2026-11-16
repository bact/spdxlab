#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: CC0-1.0
# Build ontologies for the CreationInfo reproduction.
# usage: build.sh WORKDIR   (needs git, python3, curl)
set -euo pipefail
W=${1:?workdir}; mkdir -p "$W"; cd "$W"
here=$(cd "$(dirname "$0")" && pwd)

# after = PR heads; before = their merge-bases (see below)
fetch() {  # repo dir ref
  [ -d "$2" ] || git clone -q https://github.com/spdx/$1 "$2"
  git -C "$2" fetch -q origin "$3" && git -C "$2" -c advice.detachedHead=false checkout -q FETCH_HEAD
}
fetch spec-parser   parser-after  pull/219/head
fetch spdx-3-model  model-after   pull/1488/head   # #1484 + CI check
# before = the PRs' merge-base with the target branch, so only the PR differs
base() {  # after-dir target-branch before-dir
  [ -d "$3" ] || git clone -q "$1" "$3"
  git -C "$1" fetch -q origin "$2"
  git -C "$3" fetch -q "$(cd "$1" && pwd)" "$(git -C "$1" merge-base HEAD FETCH_HEAD)"
  git -C "$3" -c advice.detachedHead=false checkout -q FETCH_HEAD
}
base parser-after main    parser-before
base model-after  develop model-before
echo "before: spec-parser $(git -C parser-before rev-parse --short HEAD), spdx-3-model $(git -C model-before rev-parse --short HEAD)"
echo "after:  spec-parser $(git -C parser-after rev-parse --short HEAD), spdx-3-model $(git -C model-after rev-parse --short HEAD)"

[ -x venv/bin/python ] || { python3 -m venv venv; venv/bin/pip install -q -r parser-after/requirements.txt pyshacl; }
curl -sSfL -o 301.ttl https://spdx.org/rdf/3.0.1/spdx-model.ttl

gen() {  # parser model out
  rm -rf "out-$3"; venv/bin/python "$1/main.py" -r -R "out-$3" "$2/model" >"out-$3.log" 2>&1 \
    || { echo "generation failed: $3"; tail -3 "out-$3.log"; exit 1; }
  cp "out-$3/spdx-model.ttl" "$3.ttl"
}
gen parser-before model-before before
gen parser-after  model-after  after

# a new individual added in 3.1 (issue 5)
add_new() {  # model-dir extra-metadata
  rm -rf "$1-new"; cp -r "$1" "$1-new"
  f="$1-new/model/Core/Individuals/RedactedElement.md"
  sed -e 's/NoneElement/RedactedElement/g' -e '/^- specVersion:/d' -e '/^- created:/d' \
    "$1/model/Core/Individuals/NoneElement.md" > "$f"
  [ -z "$2" ] || sed -i "s/^- type: IndividualElement$/- type: IndividualElement\n$2/" "$f"
}
add_new model-before ""
add_new model-after  '- specVersion: 3.1\n- created: 2026-03-01T00:00:00Z'
gen parser-before model-before-new before-new
gen parser-after  model-after-new  after-new

# a later build that changes created but keeps specVersion (issue 2)
rm -rf model-after-edit; cp -r model-after model-after-edit
sed -i 's/^- created: 2024-11-22T03:00:01Z$/- created: 2026-03-01T00:00:00Z/' model-after-edit/model/Core/Individuals/NoneElement.md
gen parser-after model-after-edit after-edit
# a later build that changes createdBy only (issue 2)
rm -rf model-after-edit-by; cp -r model-after model-after-edit-by
sed -i 's|^- createdBy: /Core/SpdxOrganization$|- createdBy: /Core/NoAssertionAgent|' model-after-edit-by/model/Core/Individuals/NoneElement.md
sed -e 's/SpdxOrganization/NoAssertionAgent/g' -e 's/^- type: Organization$/- type: Agent/' -e '/^- IRI:/d' \
  -e 's|^- createdBy: /Core/NoAssertionAgent$|- createdBy: /Core/SpdxOrganization|' \
  model-after/model/Core/Individuals/SpdxOrganization.md > model-after-edit-by/model/Core/Individuals/NoAssertionAgent.md
gen parser-after model-after-edit-by after-edit-by

# release series 3.1 -> 3.2 (issue 7): a 3.2 build adds WithheldElement
add_32() {  # model-dir extra-metadata
  rm -rf "$1-32"; cp -r "$1-new" "$1-32"
  f="$1-32/model/Core/Individuals/WithheldElement.md"
  sed -e 's/RedactedElement/WithheldElement/g' -e '/^- specVersion:/d' -e '/^- created:/d' \
    "$1-new/model/Core/Individuals/RedactedElement.md" > "$f"
  [ -z "$2" ] || sed -i "s/^- type: IndividualElement$/- type: IndividualElement\n$2/" "$f"
}
add_32 model-before ""
add_32 model-after '- specVersion: 3.2\n- created: 2027-01-22T00:00:00Z'
# without the fix, a 3.2 release bumps the hard-wired values, as 24339e1 did for 3.1
rm -rf parser-before-32; cp -r parser-before parser-before-32
sed -i -e 's|rdf/3.1/creationInfo_|rdf/3.2/creationInfo_|' -e 's|Literal("3.1")|Literal("3.2")|' \
  -e 's|2026-01-23T03:01:00Z|2027-01-22T00:00:00Z|' parser-before-32/spec_parser/rdf.py
[ "$(grep -c -e 'rdf/3.2/creationInfo_' -e 'Literal("3.2")' -e '2027-01-22T00:00:00Z' parser-before-32/spec_parser/rdf.py)" = 3 ] \
  || { echo "3.2 bump did not apply"; exit 1; }
gen parser-before-32 model-before-32 before-32
gen parser-after     model-after-32  after-32

echo "built: 301.ttl before.ttl after.ttl before-new.ttl after-new.ttl after-edit.ttl after-edit-by.ttl before-32.ttl after-32.ttl"
