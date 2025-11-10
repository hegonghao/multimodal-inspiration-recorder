allprojects {
    repositories {
        // 使用阿里云镜像源（国内加速）
        maven { url = uri("https://maven.aliyun.com/repository/google") }
        maven { url = uri("https://maven.aliyun.com/repository/public") }

        // 官方源作为备用
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)

    // Suppress Java compilation warnings from third-party libraries
    afterEvaluate {
        tasks.withType<JavaCompile>().configureEach {
            options.compilerArgs.add("-Xlint:-options")
        }
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
