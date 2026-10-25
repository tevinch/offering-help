# TUnit coverage in Visual Studio 2022 Community

Fine Code Coverage supports TUnit through **Collect TUnit** on its own tool-window toolbar. Running tests from Test Explorer does not trigger this TUnit integration. FCC reruns the tests to produce its report and editor coverage marks; you do not need to import your existing `.coverage` file.

## Visual Studio steps

These steps follow [FCC 1.1.245's documentation](https://github.com/FortuneN/FineCodeCoverage/blob/v1.1.245/README.md#prerequisites) and [released command definitions](https://github.com/FortuneN/FineCodeCoverage/blob/v1.1.245/SharedProject/Output/OutputToolWindowPackage.vsct). They have not been exercised in a Windows IDE here.

1. Use Visual Studio 2022 Community **17.13 or newer** within the 17.x series. FCC 1.1.245's released VSIX targets Community 17.13–17.x on x64 and Arm64. Install/update [Fine Code Coverage for VS2022](https://marketplace.visualstudio.com/items?itemName=FortuneNgwenya.FineCodeCoverage2022), then restart Visual Studio.
2. Open `CoverageSample.sln` and restore/build it. The sample targets .NET 8; install the .NET 8 SDK if needed.
3. Open **View → Other Windows → Fine Code Coverage**. On that window's toolbar, choose **Collect TUnit** (command name `FCC.CollectTUnit`). Wait for collection to finish.
4. In the report, open `ShippingQuote.cs`. The two standard-order tests exercise `return 0` and `return 5`; the expedited `return 12` is initially missed. FCC documents a report in the tool window and covered/missed/partial indicators in the editor.
5. Add the third test below, build, and choose **Collect TUnit** again. The expedited return should become covered.

If the command is absent, check the installed extension version and VS minor version. If collection fails, check **Coverage Log** in the Fine Code Coverage window and **View → Output**, then select **FCC** in **Show output from**; those logs identify the project, executable and arguments FCC actually used. This sample has no evidence about your existing project's configuration or IDE output.

## Shared settings

`Shipping.Tests.csproj` has a direct reference to `Microsoft.Testing.Extensions.CodeCoverage` 18.12.0 so FCC can detect it even through its direct-reference fallback. TUnit 1.76.0 already includes that extension transitively; an extra reference is not generally required just to enable coverage.

The test project evaluates an absolute path to `coverage.config` and passes it through `FCCTestingPlatformCommandLineArguments`:

```xml
<CoverageSettingsPath>$([System.IO.Path]::GetFullPath('$(MSBuildProjectDirectory)/../coverage.config'))</CoverageSettingsPath>
<FCCTestingPlatformCommandLineArguments>--coverage-settings &quot;$(CoverageSettingsPath)&quot; --minimum-expected-tests 2</FCCTestingPlatformCommandLineArguments>
```

FCC reads that MSBuild property (or `TestingPlatformCommandLineArguments` as a fallback), uses the existing settings file, and chooses its own coverage output path/format. Test Explorer's selected runsettings are not intercepted for TUnit. The supplied configuration includes only `Shipping.dll` and excludes `obj` sources, keeping tests and framework code out of this example's report. Adapt the module inclusion to your own library name.

## Run the same coverage collector from a terminal

From this directory, the following commands work in Bash or PowerShell. Use a .NET 8 SDK in the 8.0.4xx feature band; `global.json` permits its latest installed patch. Restore uses only nuget.org.

```sh
dotnet restore CoverageSample.sln
dotnet build CoverageSample.sln --no-restore
dotnet Shipping.Tests/bin/Debug/net8.0/Shipping.Tests.dll --disable-logo --list-tests json
dotnet Shipping.Tests/bin/Debug/net8.0/Shipping.Tests.dll --disable-logo --minimum-expected-tests 2 --show-test-results all --coverage --coverage-output-format cobertura --coverage-settings "$PWD/coverage.config" --results-directory "$PWD/artifacts/baseline" --coverage-output coverage.cobertura.xml
```

The last command uses the same Microsoft.Testing.Platform coverage options as [FCC's released runner](https://github.com/FortuneN/FineCodeCoverage/blob/v1.1.245/SharedProject/Core/MsTestPlatform/TestingPlatform/TUnit/TUnitCoverageRunner.cs). Use the absolute settings path shown: a relative path can fail when the test host changes its working directory. `--coverage-output` is a **filename**, placed in the explicit results directory.

Expect **2 tests, 2 succeeded, 0 failed, 0 skipped**, exit code 0, and a new `artifacts/baseline/coverage.cobertura.xml`. The XML should contain the `Shipping` package, `Shipping.ShippingQuote` class, `Calculate` method, and source-line entries. For the unchanged sample, line 9 (`return 12`) has zero hits; lines 14 and 17 have positive hits. The native check produced 7/9 covered lines and 3/4 covered branches. An empty `<packages />` is not a successful coverage result, even if the tests passed. Use a fresh results directory when checking a new run so an older XML cannot disguise a failed collection.

An interrupted or invalid collection can leave instrumented output behind. If coverage remains empty after correcting the invocation, restore/build a fresh copy of this sample and collect again. Do not treat an existing report as proof of a new run.

### Cover the missed path

Add this method inside `ShippingQuoteTests` in `Shipping.Tests/ShippingQuoteTests.cs`:

```csharp
[Test]
public async Task Expedited_order_costs_twelve()
{
    await Assert.That(ShippingQuote.Calculate(50, expedited: true)).IsEqualTo(12);
}
```

Build and collect into a separate directory:

```sh
dotnet build CoverageSample.sln --no-restore
dotnet Shipping.Tests/bin/Debug/net8.0/Shipping.Tests.dll --disable-logo --minimum-expected-tests 3 --show-test-results all --coverage --coverage-output-format cobertura --coverage-settings "$PWD/coverage.config" --results-directory "$PWD/artifacts/expanded" --coverage-output coverage.cobertura.xml
```

Expect **3 tests, 3 succeeded**, and positive hits for line 9 in `artifacts/expanded/coverage.cobertura.xml`. The unchanged library now has 9/9 covered lines and 4/4 covered branches. In Visual Studio, rerun **Collect TUnit** after adding the test; FCC produces its own report.

## What was checked

Native command-line checks used macOS Arm64, .NET SDK **8.0.426** / runtime **8.0.32**, TUnit **1.76.0**, and Microsoft.Testing.Extensions.CodeCoverage **18.12.0**. A clean consumer build, exact test counts, source/method hits, the added-test change, and negative controls for nonmatching module inclusion, omitted coverage and a filter selecting no tests were checked. Windows extension installation, toolbar use and editor indicators remain documented steps, not verified UI results. No `.coverage` conversion or HTML coverage viewer is required by this example.

Coverage records which instrumented code ran. It does not establish that assertions are sufficient or that the code is correct.

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
