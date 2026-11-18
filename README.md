---
SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
SPDX-FileType: DOCUMENTATION
SPDX-License-Identifier: CC0-1.0
---

# Experiments on SPDX

Reproductions for issues and experiments on the SPDX specification,
model and tooling.
Each folder is self-contained, with its own README, scripts and
expected output.

A personal lab, not an official SPDX project.

| Folder | Issue | Fixes |
| --- | --- | --- |
| [creationinfo](creationinfo/) | Mutable `CreationInfo` of spec-defined individuals breaks merging ontologies of different SPDX 3 versions ([spdx/spdx-3-model#1465](https://github.com/spdx/spdx-3-model/issues/1465)) | [spdx/spec-parser#219](https://github.com/spdx/spec-parser/pull/219), [spdx/spdx-3-model#1484](https://github.com/spdx/spdx-3-model/pull/1484), [spdx/spdx-3-model#1488](https://github.com/spdx/spdx-3-model/pull/1488) |
| [context-vocab](context-vocab/) | Class-valued properties typed `@vocab` in the JSON-LD context turn element ids that match a term name into SPDX term IRIs ([spdx/spec-parser#204](https://github.com/spdx/spec-parser/issues/204), [spdx/spdx-3-model#1167](https://github.com/spdx/spdx-3-model/issues/1167)) | [spdx/spec-parser#205](https://github.com/spdx/spec-parser/pull/205) |
