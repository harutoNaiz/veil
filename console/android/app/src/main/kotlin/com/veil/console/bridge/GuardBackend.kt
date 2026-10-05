package com.veil.console.bridge

/** What the Guard must offer the app. Chapter 4/5 plugs the real Guard in behind this. */
interface GuardBackend {
    fun hello(): HelloMsg
    fun getState(): StateMsg
    fun start()
    fun stop()
    fun setMode(mode: String)
    fun setSkipList(packages: List<String>)
    fun installedApps(): List<InstalledAppMsg>
    fun compilePack(text: String, photos: List<FileRefMsg>): ConceptMsg
    fun setConceptPack(pack: FileRefMsg): String
    fun submitFeedback(coverId: String, kind: String)
    fun recentCovers(limit: Long): List<RecentCoverMsg>
    fun requestPermission(perm: String)
}
