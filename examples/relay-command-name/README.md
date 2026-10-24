# Bind to the generated RelayCommand name

For a method named `OnPointerPressed`, `[RelayCommand]` generates **`PointerPressedCommand`**. Bind to that property:

```xml
<Button Command="{Binding PointerPressedCommand}" />
```

The method keeps its original name. The generated property's name has its `On` prefix removed, as described in the [MVVM Toolkit documentation](https://learn.microsoft.com/en-us/dotnet/communitytoolkit/mvvm/generators/relaycommand).

| Method | Generated command |
| --- | --- |
| `OnPointerPressed()` | `PointerPressedCommand` |
| `AsdfPointerPressed()` | `AsdfPointerPressedCommand` |

Binding to `OnPointerPressedCommand` asks Avalonia for a property that was not generated. That compiled-binding error does not, by itself, mean the generator failed.

## Complete example

`TestViewModel.cs` contains both methods. `TestWindow.axaml` uses real compiled bindings, with the view model supplied through `DataContext`. Each method updates a displayed counter so the effect can be observed.

The executable loads that XAML into an Avalonia headless window and sends pointer input through the official headless API. It does not call either generated command or handler directly. Its JSON output records the view model counts, displayed `TextBlock` text and independently observed Button click events.

Uses CommunityToolkit.Mvvm **8.4.2**, Avalonia/Headless/SimpleTheme **12.1.4**, .NET 10 and C# 13. Dependencies are fixed in `packages.lock.json`.

```sh
python3 verify.py
```

Requires the .NET 10 SDK and Python 3. Set `DOTNET` to the SDK executable if it is not on `PATH`.

The checks:

1. Compile the complete XAML consumer and send two pointer clicks. The displayed main count changes from `0` to `1` to `2`.
2. Replace `DataContext`, observe `0`, click again and observe `1`. The old view model stays at `2`.
3. Click the second button and observe its independent `AsdfPointerPressedCommand` count reach `1`.
4. Build a temporary copy using the original `OnPointerPressedCommand` binding. It must fail with Avalonia `AVLN2000` for that missing member.
5. Remove the command binding in another copy: Button clicks still occur, but the counter does not change, so validation must fail.
6. Omit pointer presses in another copy: the final UI checks must fail.

To inspect the headless result without the failure controls:

```sh
dotnet restore --locked-mode
dotnet run -c Release --no-restore
```

The executable is a small validation consumer, not a desktop launcher. Copy the corrected binding and the relevant view model method into your existing application. Its normal desktop startup remains responsible for creating the view and setting its `DataContext`.

Checked with .NET SDK 10.0.402 on macOS arm64. These are scripted headless UI checks, not a Windows desktop run, human testing or confirmation from the original application. The [motivating report](https://github.com/CommunityToolkit/dotnet/issues/1215) used Avalonia 12.1.3; this consumer uses 12.1.4 while keeping the same Toolkit version.

Reference: [Avalonia's headless Button input tests](https://github.com/AvaloniaUI/Avalonia/blob/master/tests/Avalonia.Headless.UnitTests/InputTests.cs).

## Optional coffee

If this example saves you some time, you're welcome to buy me a coffee. It is entirely optional; the example stays free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
