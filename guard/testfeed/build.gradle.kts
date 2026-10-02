plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "com.veil.testfeed"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.veil.testfeed"
        minSdk = 31
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }
    buildTypes {
        release { isMinifyEnabled = false }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    testImplementation(libs.junit)
}
