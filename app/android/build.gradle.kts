import com.android.build.api.dsl.ApplicationExtension
import com.android.build.api.dsl.LibraryExtension

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

    // Older ML Kit plugins declare compileSdk 29/31, which cannot compile
    // their current Android resources (for example android:attr/lStar).
    // Keep every Android module on the app's supported SDK instead.
    plugins.withId("com.android.application") {
        extensions.configure<ApplicationExtension> {
            compileSdk = 36
        }
    }
    plugins.withId("com.android.library") {
        extensions.configure<LibraryExtension> {
            compileSdk = 36
        }
    }

    // Plugin build scripts may assign their legacy compileSdkVersion after
    // the Android plugin is applied; apply the project-wide value last.
    afterEvaluate {
        extensions.findByType<ApplicationExtension>()?.compileSdk = 36
        extensions.findByType<LibraryExtension>()?.compileSdk = 36
    }

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
