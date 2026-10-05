package com.veil.soak

import java.io.File
import kotlin.math.ceil
import kotlin.math.sqrt

data class SoakRow(
    val tMs: Long,
    val lookMs: Double,
    val ok: Boolean,
    val pssKb: Long,
    val thermal: Int,
    val headroom: Double
)

data class SoakResult(
    val looks: Int,
    val errors: Int,
    val growthPct: Double,
    val firstMinP95: Double,
    val lastMinP95: Double,
    val driftPct: Double,
    val maxThermal: Int,
    val pass: Boolean
)

/** Nearest rank: sorted[ceil(p*n)-1]. */
fun percentile(values: List<Double>, p: Double): Double {
    if (values.isEmpty()) return 0.0
    val s = values.sorted()
    return s[(ceil(p * s.size).toInt() - 1).coerceIn(0, s.size - 1)]
}

private fun median(v: List<Long>): Double {
    if (v.isEmpty()) return 0.0
    val s = v.sorted()
    return if (s.size % 2 == 1) s[s.size / 2].toDouble() else (s[s.size / 2 - 1] + s[s.size / 2]) / 2.0
}

private fun pct(from: Double, to: Double) = if (from <= 0.0) 0.0 else (to - from) / from * 100.0

private fun dataLines(text: String) = text.lineSequence().drop(1).filter {
    it.isNotBlank()
}.map { it.trim().split(',') }

object SoakAnalyzer {
    private const val WINDOW_MS = 60_000L

    fun analyze(rows: List<SoakRow>, warmupMs: Long = 60_000): SoakResult {
        if (rows.isEmpty()) return SoakResult(0, 0, 0.0, 0.0, 0.0, 0.0, 0, false)
        val t0 = rows.first().tMs
        val end = rows.last().tMs
        val seconds = (end - t0) / 1000.0
        val errors = rows.count { !it.ok }
        val after = rows.filter { it.tMs - t0 >= warmupMs }
        val first = after.filter { it.tMs - t0 < warmupMs + WINDOW_MS }
        val last = after.filter { it.tMs > end - WINDOW_MS }
        val growth = pct(median(first.map { it.pssKb }), median(last.map { it.pssKb }))
        val p95a = percentile(first.map { it.lookMs }, 0.95)
        val p95b = percentile(last.map { it.lookMs }, 0.95)
        val drift = pct(p95a, p95b)
        val pass = errors == 0 && growth <= 5.0 && drift <= 20.0 && rows.size >= 0.95 * 3 * seconds
        return SoakResult(rows.size, errors, growth, p95a, p95b, drift, rows.maxOf { it.thermal }, pass)
    }

    fun parse(text: String): List<SoakRow> = dataLines(text).map {
        SoakRow(
            it[0].toLong(),
            it[1].toDouble(),
            it[2] == "true" || it[2] == "1",
            it[3].toLong(),
            it[4].toInt(),
            it[5].toDouble()
        )
    }.toList()
}

data class TimingRow(val runtime: String, val model: String, val phase: String, val i: Int, val ms: Double)

object TimingReport {
    fun parse(text: String): List<TimingRow> = dataLines(text).map {
        TimingRow(it[0], it[1], it[2], it[3].toInt(), it[4].toDouble())
    }.toList()

    private fun lookMs(rows: List<TimingRow>) = rows.filter { it.model == "look" && it.phase == "warm" }.map { it.ms }

    fun pass(rows: List<TimingRow>): Boolean {
        val look = lookMs(rows)
        return look.isNotEmpty() && percentile(look, 0.95) <= 45.0
    }

    fun markdown(rows: List<TimingRow>): String {
        val sb = StringBuilder("| runtime | model | phase | n | p50 ms | p95 ms |\n|---|---|---|---|---|---|\n")
        rows.groupBy { Triple(it.runtime, it.model, it.phase) }
            .toSortedMap(compareBy({ it.first }, { it.second }, { it.third }))
            .forEach { (k, v) ->
                val ms = v.map { it.ms }
                sb.append(
                    "| ${k.first} | ${k.second} | ${k.third} | ${ms.size} | %.2f | %.2f |\n".format(
                        percentile(ms, 0.5),
                        percentile(ms, 0.95)
                    )
                )
            }
        sb.append(
            "\nGate: look p95 <= 45 ms: %.2f ms -> %s\n".format(
                percentile(lookMs(rows), 0.95),
                if (pass(rows)) "PASS" else "FAIL"
            )
        )
        return sb.toString()
    }
}

object FpParity {
    private fun load(text: String): Map<String, DoubleArray> = dataLines(text).associate {
        it[0] to DoubleArray(it.size - 1) { i -> it[i + 1].toDouble() }
    }

    fun cosine(a: DoubleArray, b: DoubleArray): Double {
        var d = 0.0
        var na = 0.0
        var nb = 0.0
        for (i in a.indices) {
            d += a[i] * b[i]
            na += a[i] * a[i]
            nb += b[i] * b[i]
        }
        return d / (sqrt(na) * sqrt(nb))
    }

    /** Minimum cosine over images present in both files; -1 when nothing matches. */
    fun minCosine(phone: String, laptop: String): Double {
        val l = load(laptop)
        return load(phone).mapNotNull { (k, v) -> l[k]?.let { cosine(v, it) } }.minOrNull() ?: -1.0
    }
}

private fun finish(tag: String, ok: Boolean, detail: String): Nothing {
    println(detail)
    println("$tag: ${if (ok) "PASS" else "FAIL"}")
    kotlin.system.exitProcess(if (ok) 0 else 1)
}

fun soakMain(args: Array<String>) {
    val r = SoakAnalyzer.analyze(SoakAnalyzer.parse(File(args[0]).readText()))
    finish("SOAK", r.pass, r.toString())
}

fun timingMain(args: Array<String>) {
    val rows = TimingReport.parse(File(args[0]).readText())
    finish("TIMING", TimingReport.pass(rows), TimingReport.markdown(rows))
}

fun parityMain(args: Array<String>) {
    val m = FpParity.minCosine(File(args[0]).readText(), File(args[1]).readText())
    finish("PARITY", m >= 0.98, "min cosine = $m")
}
