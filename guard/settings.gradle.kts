pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "veil-guard"
include(":brain")
if (file("conductor/build.gradle.kts").exists()) include(":conductor")
if (file("teacher/build.gradle.kts").exists()) include(":teacher")
if (file("runtime/build.gradle.kts").exists()) include(":runtime")
if (file("soak/build.gradle.kts").exists()) include(":soak")
if (!providers.gradleProperty("veil.brainOnly").isPresent) {
    include(":app")
    if (file("smoketest/build.gradle.kts").exists()) include(":smoketest")
    if (file("testfeed/build.gradle.kts").exists()) include(":testfeed")
}
