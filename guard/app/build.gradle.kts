plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "com.veil.guard"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.veil.guard"
        minSdk = 31
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    buildTypes {
        release { isMinifyEnabled = false }
    }
    sourceSets.getByName("androidTest").assets.directories.add("../../contracts/tapes")
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation(project(":brain"))
    implementation(project(":teacher"))
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.8.1")
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.22.0")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("junit:junit:4.13.2")
    implementation(libs.kotlinx.coroutines.android)
    testImplementation(libs.junit)
}
