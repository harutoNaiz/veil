package com.veil.conductor

import com.veil.brain.contract.Finding

/**
 * Runs every lane; one that throws is logged as a warn and skipped, so the other lanes' findings survive.
 * (A bad concept once threw `ArrayIndexOutOfBoundsException` and took the NSFW lane's findings down with it.)
 */
fun runLanesIsolated(lanes: List<Lane>, input: LookInput, log: DebugLog?): List<Finding> = lanes.flatMap { lane ->
    try {
        lane.run(input)
    } catch (e: Exception) {
        val name = lane.javaClass.simpleName.ifEmpty { lane.javaClass.name }
        log?.write(
            linkedMapOf("kind" to "warn", "what" to "lane-failed", "lane" to name, "why" to e.toString())
        )
        emptyList()
    }
}
