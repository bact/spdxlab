# SPDX lab

Reproductions and experiments for issues in the SPDX specification, model and
tooling. Each folder is self-contained, with its own README, scripts and
expected output.

A personal lab, not an official SPDX project.

| Folder | Issue | Fixes |
| --- | --- | --- |
| [creationinfo](creationinfo/) | Mutable `CreationInfo` of spec-defined individuals breaks merging ontologies of different SPDX 3 versions ([spdx/spdx-3-model#1465](https://github.com/spdx/spdx-3-model/issues/1465)) | [spdx/spec-parser#219](https://github.com/spdx/spec-parser/pull/219), [spdx/spdx-3-model#1484](https://github.com/spdx/spdx-3-model/pull/1484), [spdx/spdx-3-model#1488](https://github.com/spdx/spdx-3-model/pull/1488) |

Requirements: git, python3 (with venv), curl.
