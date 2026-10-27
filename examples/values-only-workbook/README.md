# Save a workbook as values only

Assigning a cell's `Value` also removes its formula in ClosedXML. Recalculate first, then take a snapshot of **all** formula results before replacing any formulas:

```csharp
using ClosedXML.Excel;

using var workbook = new XLWorkbook("input.xlsx");
workbook.RecalculateAllFormulas();

var values = workbook.Worksheets
    .SelectMany(sheet => sheet.CellsUsed())
    .Where(cell => cell.HasFormula)
    .Select(cell => (Cell: cell, Value: cell.Value))
    .ToList();

foreach (var item in values)
    item.Cell.Value = item.Value;

workbook.SaveAs("values.xlsx");
```

Use this pattern for ordinary scalar formulas that ClosedXML can calculate. `XLCellValue` retains the result's type; converting everything to a string would change numbers and booleans. The existing cell styles and number formats remain in place. `CachedValue` can be stale, so it is not a replacement for recalculation when current results are required.

The complete command below adds checks for the limited scope of this example and refuses existing output paths. Keep a backup of important workbooks and use a new output filename.

## Run the example

From this directory, with the .NET 8 SDK (or a newer SDK **and** the .NET 8 runtime):

```sh
dotnet restore --locked-mode
dotnet build --no-restore
dotnet run --no-build -- input.xlsx values.xlsx
```

The project pins ClosedXML **0.105.1** and its dependency lock. The command loads the input, recalculates, snapshots the formula results, replaces formulas, and serializes a new workbook. It leaves the input file untouched. The destination's parent directory must already exist.

This small consumer deliberately stops for array/data-table formulas, formula-bearing Excel tables, calculation errors and unsupported functions. Those cases need a workflow suited to the workbook. It does not use Excel, refresh external data, or provide an Excel-compatible calculation engine. The first short snippet omits these checks; use the complete consumer when you want the stated refusal behavior. Named formulas, charts, validation rules and conditional formatting are outside the scope of removing **cell** formulas.

ClosedXML loads the workbook into memory; this command also serializes to memory before creating the destination. It is intended for workbooks that fit comfortably in memory.

## Check with real files

```sh
dotnet run --no-build -- --check check-output
```

Use a new directory name for another run. The check creates a two-sheet workbook with six dependent number, text, boolean and date formulas, deliberately stale cached values, literal cells, formatting and a merged note. It exports the same input twice, reopens both outputs, checks the exact typed results, inspects the worksheet XML for remaining cell formulas, and verifies that the source bytes are unchanged. It also checks the refusal cases and existing-output protection.

Expected final line:

```text
PASS: two real file exports, six typed formula results, unchanged content/source, no serialized formulas, and seven refusal cases.
```

The checks ran with .NET SDK 8.0.426 and ClosedXML 0.105.1 on macOS arm64. They are native library and file checks; Excel's desktop interface and the requester's workbook were not tested.

## References

- [ClosedXML formula calculation and the difference between Value and CachedValue](https://github.com/ClosedXML/ClosedXML/blob/0.105.1/docs/concepts/formula-calculation.rst)
- [Value setter documentation in ClosedXML 0.105.1](https://github.com/ClosedXML/ClosedXML/blob/0.105.1/ClosedXML/Excel/Cells/IXLCell.cs)
- [Original values-only usage question](https://github.com/ClosedXML/ClosedXML/discussions/2816)

The example code uses this repository's MIT license.

## Optional coffee

This example is free. If it saved you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
