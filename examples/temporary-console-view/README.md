# A temporary console view with a selection

Show several static widgets while a `SelectionPrompt` is active, then return
the actual choice and restore the preceding console screen. Spectre.Console's
native `AlternateScreen` keeps the view and prompt in a temporary screen buffer.

This is a temporary full-screen view: the main screen is hidden while it is
open, then restored. It does not erase arbitrary widgets from inline output.
The two panels here are static; no live display, status or progress component
runs alongside the prompt.

## Run

Requires .NET 10 and an interactive terminal that supports ANSI and an alternate
screen buffer, with at least **60 columns and 18 rows**.

```sh
dotnet restore --locked-mode --configfile NuGet.Config
dotnet run --no-restore -c Release
```

Press Enter to open the view. Both panels remain visible above the three
choices. Use the arrow keys and Enter to choose. After selection, the panels
and prompt disappear and `Returned 1: <choice>` appears beside the original
main-screen content. Open it again to make another choice; the first result
remains visible when you return.

The dependency is pinned to **Spectre.Console 0.57.2** in the project and lock
file. The example does not force capability overrides or change saved terminal
preferences. Redirected input/output, an unsupported terminal, or a smaller
terminal produces an explanation and exit code 2 before opening the view.
Existing output is preserved; there is no clearing fallback.

## Use the native API

The core of [TemporaryView.cs](TemporaryView.cs) is:

```csharp
string? selected = null;
console.AlternateScreen(() =>
{
    console.Write(widgets); // a bounded, static renderable
    selected = console.Prompt(new SelectionPrompt<string>()
        .Title("Choose a destination")
        .PageSize(3)
        .AddChoices("Alpha", "Beta", "Gamma"));
});
// The main screen has been restored. Use selected here.
```

The complete method checks capabilities and available space, constructs a
bounded two-panel `Grid`, and returns the selected string after the callback.
The caller prints that result on the restored main screen. The native API
exits the alternate buffer in a `finally` block if its callback throws.

Keep this fixed view at or above the stated size while it is open. Its two
panels occupy four rows, followed by a blank line and the prompt. A default
full-height `Layout`, long text, more widgets or a larger prompt can consume
the space needed to keep everything visible. Recalculate your own layout's
row budget rather than copying the minimum size for unrelated content.
This example does not handle resizing during a prompt or provide a general
inline widget-removal system.

## Verify the interaction

The optional check requires macOS or Linux with a POSIX PTY, Python 3.9+,
Node.js 20+ and npm. It runs the real .NET executable and sends real keyboard
input through a PTY. A pinned headless xterm terminal interprets the output;
the check inspects the active and saved main screen, not just escape tokens.

```sh
dotnet build --no-restore -c Release
npm ci --prefix validation --ignore-scripts --no-audit --no-fund
python3 validation/verify.py --assembly bin/Release/net10.0/TemporaryConsoleView.dll
```

At 80×24 and 60×18, it checks that both widgets and all choices are visible
together, selects **Beta** and then **Gamma**, verifies the exact returned
values, and confirms that original content and the first result survive the
second view. It also checks narrow/short terminals, `TERM=dumb`, and redirected
input/output. The validator closes only the processes it starts. Pass
`--output /path/to/results.json` to save terminal screen snapshots.

Validated by software-operated terminal checks on macOS arm64 with .NET SDK
10.0.402 and `@xterm/headless` 6.0.0. This is not human terminal testing or
confirmation from another application's user. Other operating systems,
terminal implementations and dynamic resizing have not been validated here.

Sources: the official [alternate-screen example](https://github.com/spectreconsole/examples/blob/main/examples/Console/AlternateScreen/Program.cs),
the stable [native alternate-buffer implementation](https://github.com/spectreconsole/spectre.console/blob/bbbb5729dde27b58deee44f447a788eea46ee451/src/Spectre.Console/Extensions/AnsiConsoleExtensions.Screen.cs),
and the official [selection-prompt guidance](https://github.com/spectreconsole/website/blob/main/Spectre.Docs/Content/console/prompts/selection-prompt.md).
The source is [MIT licensed](LICENSE).

## Optional coffee

The example is free. If it helps, you can optionally buy me a coffee:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
