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
if (file("teacher/build.gradle.kts").exists()) include(":teacher")
if (!providers.gradleProperty("veil.brainOnly").isPresent) {
    include(":app")
    if (file("testfeed/build.gradle.kts").exists()) include(":testfeed")
}
