buildscript {
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        // AGP 9 built-in Kotlin; pin KGP to Flutter 3.47.6's version (see SPEC R2 for the fallback)
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:2.4.0")
    }
}
plugins {
    alias(libs.plugins.android.application) apply false
}
