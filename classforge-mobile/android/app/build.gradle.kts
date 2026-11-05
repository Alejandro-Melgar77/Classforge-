plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.classforge.classforge_mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = "28.2.13676358"

    compileOptions {
        isCoreLibraryDesugaringEnabled = true
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = "com.classforge.classforge_mobile"
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            isShrinkResources = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

tasks.matching { it.name.startsWith("assemble") }.configureEach {
    doLast {
        val flutterApkDir = file("${layout.buildDirectory.asFile.get()}/outputs/flutter-apk")
        if (flutterApkDir.exists()) {
            flutterApkDir.listFiles()?.forEach { apk ->
                if (apk.extension == "apk" && !apk.name.startsWith("Classforge-Visualizer")) {
                    apk.copyTo(file("${flutterApkDir.path}/Classforge-Visualizer.apk"), overwrite = true)
                }
            }
        }
    }
}

flutter {
    source = "../.."
}

dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")
}
