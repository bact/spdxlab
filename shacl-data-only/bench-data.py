# SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
# SPDX-License-Identifier: CC0-1.0
"""Write a large test document: N packages, files and relationships, one bad package per 1000.

Usage: python bench-data.py N OUT.ttl   (N = 20000 gives 60k elements)
"""

import sys

HEAD = """@prefix c: <https://spdx.org/rdf/3/terms/Core/> .
@prefix s: <https://spdx.org/rdf/3/terms/Software/> .
@prefix h: <https://spdx.org/rdf/3/terms/Core/HashAlgorithm/> .
@prefix r: <https://spdx.org/rdf/3/terms/Core/RelationshipType/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <https://example.org/doc/> .

ex:Person a c:Person ; c:creationInfo ex:ci ; c:name "Jane Doe" .
ex:ci a c:CreationInfo ; c:specVersion "3.1" ;
    c:created "2026-11-18T00:00:00Z"^^xsd:dateTimeStamp ; c:createdBy ex:Person .
"""
SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def main():
    n, out = int(sys.argv[1]), sys.argv[2]
    with open(out, "w") as f:
        f.write(HEAD)
        for i in range(n):
            f.write(f'ex:P{i} a s:Package ; c:creationInfo ex:ci ; c:name "p{i}" ;\n'
                    f"    c:verifiedUsing [ a c:Hash ; c:algorithm h:sha256 ; c:hashValue \"{SHA}\" ] .\n")
            f.write(f'ex:F{i} a s:File ; c:creationInfo ex:ci ; c:name "f{i}" .\n')
            f.write(f"ex:R{i} a c:Relationship ; c:creationInfo ex:ci ;\n"
                    f"    c:from ex:P{i} ; c:to ex:F{i} ; c:relationshipType r:contains .\n")
            if i % 1000 == 0:
                f.write(f'ex:Bad{i} a s:Package ; c:name "no creationInfo" .\n')


if __name__ == "__main__":
    main()
