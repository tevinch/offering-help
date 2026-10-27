# Select a .NET 10.0.4xx SDK

An up-to-date `10.0.1xx` SDK can still be too old for a tool that requires `10.0.4xx`. In the [reported C# Dev Kit case](https://github.com/microsoft/vscode-dotnettools/issues/3619), the maintainer identified SDK `10.0.112` and required `10.0.400` or later. These are different SDK feature bands; installing a newer .NET runtime alone does not supply the required SDK. [SDK versioning](https://learn.microsoft.com/en-us/dotnet/core/porting/versioning-sdk-msbuild-vs) explains the numbering.

`apt update` and `apt upgrade` work with the packages and candidates available through your configured sources. They do not guarantee that a particular SDK feature band is available, installed or selected by your editor. Your Ubuntu version, package origin, package policy, selected `dotnet` host and project configuration need separate checks. The report does not establish which of these applies.

## Check before changing anything

Run these read-only commands on the Ubuntu machine:

```sh
cat /etc/os-release
uname -m
apt-cache policy dotnet-sdk-10.0
apt-mark showhold
type -a dotnet
readlink -f "$(command -v dotnet)"
dotnet --list-sdks
```

[`apt-cache policy`](https://manpages.ubuntu.com/manpages/resolute/man8/apt-cache.8.html) shows the installed version, candidate and package origins. If the candidate is still `10.0.1xx`, repeating an upgrade cannot select `10.0.4xx` from that candidate. If a newer candidate exists, inspect holds and package policy before deciding how to upgrade. Do not infer your configuration from another Ubuntu release's package list.

From your actual solution directory, also run:

```sh
dotnet --version
dotnet --info
dotnet msbuild YourProject.csproj -getProperty:NETCoreSdkVersion
```

Replace `YourProject.csproj` with your project. Inspect any `global.json` in the workspace or its parent directories. `--list-sdks` lists available SDKs; `--version` reports the selection for that working directory, while the MSBuild property checks the project. A project targeting `net10.0` does not itself select the `4xx` SDK band. See [global.json resolution](https://learn.microsoft.com/en-us/dotnet/core/tools/global-json).

## Obtain a suitable SDK

For a development environment, the [C# Dev Kit walkthrough](https://code.visualstudio.com/docs/csharp/get-started) provides an official SDK installation route: **Welcome: Open Walkthrough → Get Started with C# Dev Kit**. For APT, follow the [Ubuntu installation decision guide](https://learn.microsoft.com/en-us/dotnet/core/install/linux-ubuntu-decision) for your exact release and architecture. Do not mix Microsoft and Ubuntu package feeds to try to force a version.

A separate non-admin installation is another option. Microsoft's [install script](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-install-script) is intended primarily for CI and controlled installations; it does not install Linux dependencies, and APT will not maintain this separate copy. Check the [Ubuntu dependency requirements](https://learn.microsoft.com/en-us/dotnet/core/install/linux-ubuntu-install) first. The official [.NET 10 release metadata](https://builds.dotnet.microsoft.com/dotnet/release-metadata/10.0/releases.json) listed SDK **10.0.403** on October 27, 2026.

The following Bash commands allocate a new directory under your home and a new temporary script file. They do not replace the system SDK, modify package feeds, or edit your shell configuration:

```sh
sdk_install_dir=$(mktemp -d "$HOME/dotnet-10.0.403.XXXXXX") &&
sdk_script_file=$(mktemp) &&
curl --fail --location https://dot.net/v1/dotnet-install.sh --output "$sdk_script_file" &&
bash "$sdk_script_file" --version 10.0.403 --install-dir "$sdk_install_dir" --no-path &&
"$sdk_install_dir/dotnet" --list-sdks &&
"$sdk_install_dir/dotnet" --version
```

Keep the printed installation directory for future updates and editor configuration. The final command should report `10.0.403`; run it outside a project with an incompatible SDK pin. A failed install or missing Linux dependency needs attention before continuing.

## Check the project with the new host

This directory includes a small `net10.0` console project and this `global.json`:

```json
{
  "sdk": {
    "version": "10.0.400",
    "rollForward": "latestPatch",
    "allowPrerelease": false
  }
}
```

It selects the newest installed stable patch in the `10.0.4xx` band. It does not install an SDK. Review an existing application's SDK pin with its maintainers rather than replacing it with this sample's file.

From this sample directory, using the new installation variable from above:

```sh
"$sdk_install_dir/dotnet" --version
"$sdk_install_dir/dotnet" msbuild SdkSelection.csproj -getProperty:NETCoreSdkVersion
"$sdk_install_dir/dotnet" build SdkSelection.csproj
"$sdk_install_dir/dotnet" run --project SdkSelection.csproj --no-build
```

The first two commands should agree on `10.0.4xx`; the program prints `SDK selection sample ran.` You can use the same explicit host to check your real solution. Merely changing `global.json` cannot make `10.0.112` satisfy the requirement.

For C# Dev Kit, close and reopen the workspace after the SDK or pin changes. Check **Output → Projects** to see which SDK the editor actually detects. If it still detects the old location, follow the [official SDK discovery troubleshooting](https://code.visualstudio.com/docs/csharp/cs-dev-kit-faq#_the-solution-explorer-displays-a-compatible-net-sdk-was-not-found) and existing-install guidance there. A passing terminal build does not prove the editor selected the same host.

## Verification and limits

```sh
python3 verify.py /absolute/path/to/dotnet
```

The verifier copies the sample into a temporary directory, checks SDK selection and the project's SDK property, then builds and runs it. It also confirms that a missing exact SDK pin fails and leaves source files unchanged. An optional second argument is an older `dotnet` host that must fail to resolve the required SDK.

This was run on macOS with existing SDK **10.0.402**, which satisfies the same `4xx` requirement, and an older **8.0.426** host as a negative check. Ubuntu APT, the Linux installation commands and C# Dev Kit's UI were not executed. The guide does not claim that the original machine's warning has been resolved.

## Optional coffee

This guide and sample are free. If they save you time, a small coffee is welcome and entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
