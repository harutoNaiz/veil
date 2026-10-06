plugins { id("org.jetbrains.kotlin.jvm") }

kotlin { jvmToolchain(17) }

dependencies {
    implementation(project(":brain"))
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.8.1")
    compileOnly("com.microsoft.onnxruntime:onnxruntime:1.22.0")
    testImplementation("com.microsoft.onnxruntime:onnxruntime:1.22.0")
    testImplementation("ai.djl.huggingface:tokenizers:0.34.0")
    testImplementation("junit:junit:4.13.2")
}

tasks.test {
    exclude("**/TeacherParity*")
    maxHeapSize = "512m"
    systemProperty("veil.repo", rootProject.file("..").path)
}

tasks.register<Test>("teacherParity") {
    testClassesDirs = sourceSets["test"].output.classesDirs
    classpath = sourceSets["test"].runtimeClasspath
    filter.includeTestsMatching("com.veil.teacher.TeacherParity")
    systemProperty("veil.repo", rootProject.file("..").path)
    maxHeapSize = "1g"
    testLogging { showStandardStreams = true }
}
