plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "com.example.aitestapp"
    compileSdk {
        version = release(36)
    }

    defaultConfig {
        applicationId = "com.example.aitestapp"
        minSdk = 33
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
        val backendBaseUrl = (project.findProperty("BACKEND_BASE_URL") as String?) ?: "http://10.0.2.2:8000"
        val tempUserId = (project.findProperty("TEMP_USER_ID") as String?) ?: "demouser1"
        buildConfigField("String", "BACKEND_BASE_URL", "\"${backendBaseUrl.replace("\"", "\\\"")}\"")
        buildConfigField("String", "TEMP_USER_ID", "\"${tempUserId.replace("\"", "\\\"")}\"")

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    kotlinOptions {
        jvmTarget = "11"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }

    // [중요] 모델 파일 압축 방지 및 대용량 파일 허용
    aaptOptions {
        noCompress("litertlm", "tflite")
    }

    packagingOptions {
        jniLibs {
            useLegacyPackaging = true
        }
    }



}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.tooling)
    debugImplementation(libs.androidx.compose.ui.test.manifest)

    implementation("org.tensorflow:tensorflow-lite:2.16.1")
}