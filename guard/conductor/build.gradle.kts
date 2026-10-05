plugins { id("org.jetbrains.kotlin.jvm") }

kotlin { jvmToolchain(17) }

dependencies {
    implementation(project(":brain"))
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.8.1")
}

tasks.test {
    systemProperty("veil.tapes", rootProject.file("../contracts/tapes").path)
    systemProperty("veil.repo", rootProject.file("..").path)
    maxHeapSize = "512m"
}
