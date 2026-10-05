package com.veil.console.bridge

class GuardHostImpl(private val backend: GuardBackend) : GuardHostApi {
    override fun hello() = backend.hello()
    override fun getState() = backend.getState()
    override fun start() = backend.start()
    override fun stop() = backend.stop()
    override fun setMode(mode: String) = backend.setMode(mode)
    override fun setSkipList(packages: List<String>) = backend.setSkipList(packages)
    override fun installedApps() = backend.installedApps()
    override fun compilePack(text: String, photos: List<FileRefMsg>) = backend.compilePack(text, photos)
    override fun setConceptPack(pack: FileRefMsg) = backend.setConceptPack(pack)
    override fun submitFeedback(coverId: String, kind: String) = backend.submitFeedback(coverId, kind)
    override fun recentCovers(limit: Long) = backend.recentCovers(limit)
    override fun requestPermission(perm: String) = backend.requestPermission(perm)
}
