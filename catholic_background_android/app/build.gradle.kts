// SPDX-FileCopyrightText: 2026 Luis Llana <luis.llana.diaz@gmail.com>
// SPDX-License-Identifier: GPL-3.0-or-later
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

// Signature of the release (the upload key of Google Play), from ~/.gradle/gradle.properties,
// never from the repository. Without catholicBackground.storeFile the release is not signed.
val uploadStoreFile = providers.gradleProperty("catholicBackground.storeFile").orNull

android {
    namespace = "es.llana.catholicbackground"
    compileSdk = 37

    defaultConfig {
        applicationId = "es.llana.catholicbackground"
        minSdk = 26
        targetSdk = 37
        versionCode = 6
        versionName = "0.6.4"
    }

    signingConfigs {
        if (uploadStoreFile != null) {
            create("upload") {
                val password = providers.gradleProperty("catholicBackground.storePassword").get()
                storeFile = file(uploadStoreFile)
                storePassword = password
                keyAlias = providers.gradleProperty("catholicBackground.keyAlias").getOrElse("upload")
                // PKCS12 keystores (the default of keytool) use the same password for the key
                keyPassword = providers.gradleProperty("catholicBackground.keyPassword").getOrElse(password)
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            if (uploadStoreFile != null) signingConfig = signingConfigs.getByName("upload")
        }
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    testOptions {
        unitTests.isReturnDefaultValues = true
    }
}

dependencies {
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.material3)
    implementation(libs.core.ktx)
    implementation(libs.activity.compose)
    implementation(libs.lifecycle.viewmodel.compose)
    implementation(libs.lifecycle.runtime.compose)
    implementation(libs.work.runtime)

    testImplementation(libs.junit)
    // The org.json of android.jar is only a stub in unit tests
    testImplementation(libs.org.json)
}
