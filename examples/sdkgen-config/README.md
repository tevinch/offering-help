# Generate a Kotlin SDK from a local OpenAPI file

`sdkgen.yaml` is a separate, handwritten generator configuration. It points to your OpenAPI document; the OpenAPI document itself is not the configuration file.

These version fields have different jobs:

| Field | Meaning in this example |
| --- | --- |
| `openapi: 3.1.0` in `openapi.yaml` | OpenAPI document format |
| `version: v1alpha1` in `sdkgen.yaml` | SDKGen configuration format |
| Plugin/runtime `0.4.0` in `build.gradle.kts` | SDKGen release |

The API's `info.version: 1.0.0` is your API's own version. Adding `version: v1alpha1` to an OpenAPI document does not turn it into a generator configuration.

This example uses the published SDKGen **0.4.0 preview**, Kotlin and its serialization plugin **2.3.20**, and the published SDKGen runtime **0.4.0**. The small API has one `GET /books/{id}` operation and a `Book` model. The application starts a local HTTP server and calls it through the generated client.

## Run

Install JDK 21 and [Gradle 9.6.1](https://services.gradle.org/distributions/gradle-9.6.1-bin.zip), then put their executables on `PATH`. Set `JAVA_HOME` to the JDK. The Gradle archive's SHA256 is `9c0f7faeeb306cb14e4279a3e084ca6b596894089a0638e68a07c945a32c9e14`; verify it before extraction. `gradle --version` should show Gradle 9.6.1 and Java 21. The example emits Java 17 bytecode.

From this directory:

```sh
export GRADLE_USER_HOME="$(mktemp -d)"
gradle --no-daemon --max-workers=1 -Dorg.gradle.parallel=false \
  -Pkotlin.compiler.execution.strategy=in-process clean generateCatalogSdk run
```

The first run needs access to Gradle Plugin Portal and Maven Central. The example's `gradle.properties` limits the Gradle heap to 768 MiB, uses one worker and compiles Kotlin in process. Keep `GRADLE_USER_HOME` the same to reuse downloaded dependencies on subsequent runs.

Expected application output:

```text
GET /books/7 -> 200; id=7; title=山海笔记; requests=1
```

The application checks the server's received method/path and request count, actual HTTP status, and decoded integer and Unicode string. It uses the published Java HTTP transport with redirects disabled; the example sends requests only to its local server.

## Files to adapt

Keep your API description in [`openapi.yaml`](openapi.yaml). Create [`sdkgen.yaml`](sdkgen.yaml) beside it:

```yaml
version: v1alpha1
source:
  uri: openapi.yaml
  acquisition:
    mode: local
    offline: true
kotlin:
  packageName: example.catalog
  coordinates:
    groupId: example
    artifactId: catalog-client
  naming:
    clientName: CatalogClient
  targets: [jvm]
output:
  sources: build/generated/sdkgen/catalog/sources
  resources: build/generated/sdkgen/catalog/resources
  manifest: build/generated/sdkgen/catalog/manifest.json
```

`source.uri` is relative to the configuration file's directory, even when Gradle is launched elsewhere. By default local inputs stay within the config directory. If you set `allowedLocalRoots`, list every needed trusted relative root; include `.` when that directory is still needed. The current preview uses local acquisition. `offline: true` applies to specification acquisition; it does not stop Gradle from downloading plugins and dependencies.

[`build.gradle.kts`](build.gradle.kts) applies the published plugin and selects the configuration:

```kotlin
sdkgen {
    configurations {
        register("catalog") {
            configFile.set(layout.projectDirectory.file("sdkgen.yaml"))
        }
    }
}
```

The named configuration creates `generateCatalogSdk`. The plugin adds generated sources to Kotlin/JVM `main`, so `run` also triggers generation when needed. It does **not** add the SDK runtime dependency for you. This project explicitly declares `io.github.nabobery:kotlin-sdkgen-runtime:0.4.0`, the published `kotlin-sdkgen-transport-java-http:0.4.0` adapter, and the coroutine and serialization libraries used by the application/generated code.

With the Gradle plugin, `outputDirectory` owns the physical output root. Its default here is `build/generated/sdkgen/catalog`; the generated Kotlin files appear under its `sources` child. The manifest is `build/generated/sdkgen/catalog/sources/manifest.json` in this invocation. Changing only YAML `output.sources` does not move that Gradle source root. To customize it, set `outputDirectory` in the named Gradle configuration to a distinct directory strictly inside `build/`. Never point it at your handwritten `src/` tree. This invocation does not request a lock file.

## Common mistakes

- If `configFile` points to `openapi.yaml`, the task reports **“The required configuration version discriminator is missing.”** Point it to the separate `sdkgen.yaml` above.
- If `source.uri` names a nonexistent file, generation fails. Resolve it from the configuration directory, not from the shell's working directory.
- If Gradle `outputDirectory` points outside `build/`, the plugin rejects it. Use a build-owned generated directory.

To adapt the example, change the local schema and then update the consumer to use the newly generated API. Keep generated files under `build/`; do not edit them by hand.

The published preview was checked by scripted local execution with JDK 21 on macOS arm64: first-generation failure with the wrong file, generation and compiled client/model use, a real local HTTP response containing Unicode, repeated execution, an added schema field used by the consumer, and a clean copy in a directory with spaces. This does not establish compatibility with another API or an existing application's toolchain.

References: [SDKGen Gradle plugin 0.4.0](https://plugins.gradle.org/plugin/io.github.nabobery.kotlin-sdkgen/0.4.0), [configuration types](https://github.com/nabobery/kotlin-sdkgen/blob/v0.4.0/generator/engine/src/main/kotlin/com/nabobery/sdkgen/engine/config/ConfigModel.kt), [Gradle extension](https://github.com/nabobery/kotlin-sdkgen/blob/v0.4.0/integrations/gradle-plugin/src/main/kotlin/com/nabobery/sdkgen/gradleplugin/SdkGenExtension.kt).

## Optional coffee

The example is free. If it saves you time, a coffee is entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
