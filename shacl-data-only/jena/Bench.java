// SPDX-FileCopyrightText: 2026 Arthit Suriyawongkul
// SPDX-License-Identifier: CC0-1.0
// Usage: java -cp "lib/*:." Bench.java SHAPES DATA   (best of 3 runs, after a warm-up)

import org.apache.jena.graph.Graph;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.shacl.ShaclValidator;
import org.apache.jena.shacl.Shapes;
import org.apache.jena.shacl.ValidationReport;

public class Bench {
    public static void main(String[] a) {
        Shapes shapes = Shapes.parse(RDFDataMgr.loadGraph(a[0]));
        Graph data = RDFDataMgr.loadGraph(a[1]);
        ShaclValidator.get().validate(shapes, data);
        long best = Long.MAX_VALUE;
        int n = 0;
        for (int i = 0; i < 3; i++) {
            long t = System.nanoTime();
            ValidationReport r = ShaclValidator.get().validate(shapes, data);
            best = Math.min(best, System.nanoTime() - t);
            n = r.getEntries().size();
        }
        System.out.printf("%.2f s, %d results%n", best / 1e9, n);
    }
}
