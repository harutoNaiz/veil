plugins {
    id("org.jetbrains.kotlin.jvm")
    application
}

kotlin { jvmToolchain(17) }

dependencies {
    testImplementation("junit:junit:4.13.2")
}

application { mainClass.set("com.veil.soak.SoakCheckKt") }

tasks.test { maxHeapSize = "512m" }

fun mainTask(name: String, main: String) = tasks.register<JavaExec>(name) {
    classpath = sourceSets["main"].runtimeClasspath
    mainClass.set(main)
    val input = providers.gradleProperty("in").orNull
    val ref = providers.gradleProperty("ref").orNull
    args = listOfNotNull(input, ref)
}

mainTask("soakCheck", "com.veil.soak.SoakCheckKt")
mainTask("timingReport", "com.veil.soak.TimingReportKt")
mainTask("fpParity", "com.veil.soak.FpParityKt")
