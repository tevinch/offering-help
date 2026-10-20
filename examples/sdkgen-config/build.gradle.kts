plugins {
    kotlin("jvm") version "2.3.20"
    kotlin("plugin.serialization") version "2.3.20"
    application
    id("io.github.nabobery.kotlin-sdkgen") version "0.4.0"
}

repositories { mavenCentral() }

dependencies {
    implementation("io.github.nabobery:kotlin-sdkgen-runtime:0.4.0")
    implementation("io.github.nabobery:kotlin-sdkgen-transport-java-http:0.4.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.11.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.11.0")
}

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}
kotlin {
    compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) }
}

sdkgen {
    configurations {
        register("catalog") {
            configFile.set(layout.projectDirectory.file("sdkgen.yaml"))
        }
    }
}

application {
    mainClass.set("example.MainKt")
    applicationDefaultJvmArgs = listOf("-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8")
}
