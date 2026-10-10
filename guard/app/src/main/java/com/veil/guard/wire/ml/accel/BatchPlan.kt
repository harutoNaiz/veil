package com.veil.guard.wire.ml.accel

/** Picks describer batch sizes so few padded slots are computed. */
object BatchPlan {
    /** One extra run costs about this many image-slots of compute (session.run overhead). */
    private const val RUN_COST = 1.5

    /** Batch sizes (each from avail) covering n items, minimising slots + RUN_COST per run. Empty if n<=0 or avail empty. */
    fun plan(n: Int, avail: Collection<Int>): List<Int> {
        val sizes = avail.filter { it > 0 }.distinct().sorted()
        if (n <= 0 || sizes.isEmpty()) return emptyList()
        val cost = DoubleArray(n + 1)
        val pick = IntArray(n + 1)
        for (r in 1..n) {
            cost[r] = Double.MAX_VALUE
            for (b in sizes) {
                val c = cost[maxOf(0, r - b)] + b + RUN_COST
                if (c < cost[r]) {
                    cost[r] = c
                    pick[r] = b
                }
            }
        }
        val out = ArrayList<Int>()
        var r = n
        while (r > 0) {
            out += pick[r]
            r -= pick[r]
        }
        return out.sortedDescending()
    }
}
