---
SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
SPDX-FileType: DOCUMENTATION
SPDX-License-Identifier: CC0-1.0
---

# SPDX 3: mutable CreationInfo of spec-defined individuals

Reproduction for spdx/spdx-3-model#1465 and the PRs that fix it:

- spdx/spec-parser#219: read `CreationInfo` values from the model; IRI by first release
- spdx/spdx-3-model#1484: record the first-release values in the model
- spdx/spdx-3-model#1488: CI check that released values never change

## The problem in one paragraph

The spec defines five individuals: `NoAssertionElement`, `NoAssertionLicense`,
`NoneElement`, `NoneLicense` and `SpdxOrganization`. Each is an `Element`, so it
has exactly one `creationInfo` (SHACL: `Element.creationInfo` min 1, max 1).
spec-parser hard-codes that `CreationInfo` and bumps it by hand each release
(commit 24339e1, "Update hard-wired version to 3.1"). Each release therefore
gives every individual a new `CreationInfo`, although no individual changed.
Load two versions of the ontology together and every individual has two
`creationInfo` values, so the merged graph fails SHACL validation.

## 1. See it with published files (about 1 minute)

Only ontologies already published:

| Name | URL | Note |
| --- | --- | --- |
| 3.0.1 | <https://spdx.org/rdf/3.0.1/spdx-model.ttl> | release |
| 3.1-RC1 | <https://spdx.org/rdf/3.1/spdx-model.ttl> | redirects to the 3.1 RC1 build; a fixed snapshot |
| 3.1-dev | <https://spdx.github.io/spdx-spec/v3.1-dev/rdf/spdx-model.ttl> | rebuilt from `develop` |

```sh
cd creationinfo
python3 -m venv venv && venv/bin/pip install rdflib pyshacl
venv/bin/python quick.py
```

3.1-dev already uses unversioned term IRIs (`…/rdf/3/terms/…`). The 3.0.1
term IRIs (`…/rdf/3.0.1/terms/…`) are rewritten to that form, as proposed for
SPDX 3.1, so that the same individual is the same node in both files. RC1 still
uses `…/rdf/3.1/terms/…` and is rewritten the same way.

Output:

```text
1. NoneElement's CreationInfo, as published
   3.0.1    https://spdx.org/rdf/3.0.1/creationInfo_NoneElement  specVersion=3.0.1  created=2024-11-22T03:00:01Z
   3.1-RC1  https://spdx.org/rdf/3.1/creationInfo_NoneElement  specVersion=3.1  created=2026-01-23T03:01:00Z
   3.1-dev  https://spdx.org/rdf/3.1/creationInfo_NoneElement  specVersion=3.1  created=2026-01-23T03:01:00Z

2. Merged 3.0.1 + 3.1-dev: creationInfo values per individual (Element.creationInfo allows exactly 1)
   NoAssertionElement   2  (3.0.1, 3.1)
   NoneElement          2  (3.0.1, 3.1)
   SpdxOrganization     2  (3.0.1, 3.1)
   NoAssertionLicense   2  (3.0.1, 3.1)
   NoneLicense          2  (3.0.1, 3.1)

3. SHACL violations on creationInfo (shapes from 3.1-dev)
   3.0.1 alone      0
   3.1-RC1 alone    0
   3.1-dev alone    0
   3.0.1 + 3.1-RC1  5  More than 1 values on <…/Core/NoAssertionElement>-><…/Core/creationInfo>
   3.0.1 + 3.1-dev  5  More than 1 values on <…/Core/NoAssertionElement>-><…/Core/creationInfo>
```

Each file is valid on its own. Only the merges fail.

With the fix, pass an ontology built from the PRs (`work/after.ttl` from step 2):

```text
   3.0.1 + fixed    0
```

Once the PRs are merged, 3.1-dev is rebuilt with the fix and
`3.0.1 + 3.1-dev` should show 0 as well. RC1 keeps showing the issue.

## 2. Full reproduction: before and after the PRs (a few minutes)

```sh
cd creationinfo
./build.sh work                        # clone, build 9 ontologies, download 3.0.1
work/venv/bin/python -I check.py work  # issues 1-5, plus the CI check
work/venv/bin/python -I quick.py work/after.ttl
```

"Before" is the PRs' merge-base with the target branch (spec-parser `main`,
spdx-3-model `develop`), so the only difference is the PRs. "After" is the
PR heads (spec-parser#219, spdx-3-model#1488, which includes #1484).
`build.sh` makes extra models in throwaway copies: a new 3.1 individual
`RedactedElement`, a new 3.2 individual `WithheldElement`, and edits to
`NoneElement`'s `created` or `createdBy`. For a future 3.2 release without the
fix, it bumps spec-parser's hard-wired values to 3.2 in a throwaway copy, as
commit 24339e1 did for 3.1. With the fix, 3.2 needs no parser change.

| # | Issue | Before | After |
| --- | --- | --- | --- |
| 1 | Merging 3.0.1 with the new ontology fails SHACL | 5 individuals with 2 `creationInfo`; 5 violations | none; conforms |
| 2 | Same IRI, different values (why values must be frozen) | – | edited `created`: 2 values, SHACL fails; edited `createdBy`: 2 values, SHACL passes (no max), caught only by the CI check |
| 3 | 3.0.1 `CreationInfo` IRIs disappear | 5 missing | 0 missing |
| 4 | Wrong origin recorded for NoneElement | `3.1`, `2026-01-23T03:01:00Z` | `3.0.1`, `2024-11-22T03:00:01Z` |
| 5 | A new individual looks like the 3.0.1 ones | both `3.1 2026-01-23` | `3.0.1 2024-11-22` vs `3.1 2026-03-01` |
| 6 | CI check (#1488) on each build | before: FAIL (5) | after: pass; edited `created`: FAIL; edited `createdBy`: FAIL |
| 7 | Every release repeats it: 3.0.1 → 3.1 → 3.2 | see below | see below |

### Every release, not only 3.0.1 → 3.1

Without the fix, each release gives every individual it contains a new
`CreationInfo`, including individuals added in the previous release. Merging
releases collects one record per release. `x` marks an individual with more
than one `creationInfo` (`Element.creationInfo` allows exactly 1):

```text
before:
  3.1 + 3.2: SHACL violations 6
    x NoAssertionElement   creationInfo from 3.1, 3.2
    x NoAssertionLicense   creationInfo from 3.1, 3.2
    x NoneElement          creationInfo from 3.1, 3.2
    x NoneLicense          creationInfo from 3.1, 3.2
    x RedactedElement      creationInfo from 3.1, 3.2
    x SpdxOrganization     creationInfo from 3.1, 3.2
      WithheldElement      creationInfo from 3.2
  3.0.1 + 3.1 + 3.2: SHACL violations 6
    x NoAssertionElement   creationInfo from 3.0.1, 3.1, 3.2
    x NoAssertionLicense   creationInfo from 3.0.1, 3.1, 3.2
    x NoneElement          creationInfo from 3.0.1, 3.1, 3.2
    x NoneLicense          creationInfo from 3.0.1, 3.1, 3.2
    x RedactedElement      creationInfo from 3.1, 3.2
    x SpdxOrganization     creationInfo from 3.0.1, 3.1, 3.2
      WithheldElement      creationInfo from 3.2
after:
  3.0.1 + 3.1 + 3.2: SHACL violations 0
      NoAssertionElement   creationInfo from 3.0.1
      NoAssertionLicense   creationInfo from 3.0.1
      NoneElement          creationInfo from 3.0.1
      NoneLicense          creationInfo from 3.0.1
      RedactedElement      creationInfo from 3.1
      SpdxOrganization     creationInfo from 3.0.1
      WithheldElement      creationInfo from 3.2
```

`RedactedElement`, added in 3.1, breaks as soon as 3.2 is released: the
problem is not limited to the 3.0.1 individuals. With the fix, each individual
keeps the record of the release that first published it, so any combination of
releases merges cleanly. Each build is valid on its own in every case; only the
merges fail. `check.py` also prints `3.0.1 + 3.1`, and `3.1 + 3.2` with the fix.

## How the PRs fix it

- **#1484:** each individual records its first-release `CreationInfo` in the
  model: `specVersion: 3.0.1`, `created: 2024-11-22T03:00:01Z`,
  `createdBy: /Core/SpdxOrganization`.
- **#219:** spec-parser reads those values, validates them, and publishes the
  record at `https://spdx.org/rdf/{specVersion}/creationInfo_{name}`. The five
  3.0.1 IRIs stay as published. These records are not terms, so their IRIs
  carry the release version.
- **#1488:** CI generates the ontology and compares its records with each
  released ontology (release tags only; `3.1-rc1` is skipped). Any change to a
  released record fails the PR.

## Notes

- The 3.1 RC1 ontology already contains the problem. The PRs need to land
  before 3.1 final is built; otherwise the 3.1 records become released too.
- Separately, 3.1-RC1 fails SHACL on its own records: `specVersion "3.1"`
  does not match RC1's version pattern, which requires a patch number. That
  is unrelated to the merge issue, so `quick.py` counts only `creationInfo`
  violations.
- None of the `creationInfo_*` IRIs resolve on spdx.org (HTTP 404). The issue
  is in the RDF data, not in lookups on spdx.org.
