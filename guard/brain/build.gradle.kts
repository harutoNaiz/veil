plugins { id("org.jetbrains.kotlin.jvm") }

kotlin { jvmToolchain(17) }

dependencies {
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.8.1")
}

tasks.test {
    systemProperty("veil.tapes", rootProject.file("../contracts/tapes").path)
    systemProperty("veil.repo", rootProject.file("..").path)
    maxHeapSize = "512m"
}

tasks.register<Test>("tapeTest") {
    testClassesDirs = sourceSets["test"].output.classesDirs
    classpath = sourceSets["test"].runtimeClasspath
    filter.includeTestsMatching("com.veil.brain.tapes.*")
    systemProperty("veil.tapes", rootProject.file("../contracts/tapes").path)
    systemProperty("veil.repo", rootProject.file("..").path)
    maxHeapSize = "512m"
}
