# Month labels in an Excel table

This is a display workaround for ClosedXML 0.105.1: assign preformatted strings to table field names to show `Jan 2023`, `Feb 2023` and `Mar 2023`. It does not preserve date-valued table headers or provide editable Excel date formatting.

In this version, assigning a `DateTime` to an existing table header immediately converts the value to text using the current culture. Setting `NumberFormat.Format = "MMM yyyy"` on that already-converted text does not reformat it. Ordinary cells that retain `DateTime` values do support date number formats. Excel's own table conversion and date re-entry behavior were not tested here.

```csharp
var date = new DateOnly(2023, 1, 1);
table.Field(1).Name = date.ToString("MMM yyyy", CultureInfo.GetCultureInfo("en-US"));
```

Choose the culture explicitly so the generated labels do not depend on the machine's locale. If the workflow requires actual dates or editable date number formats, this example does not meet that requirement; keep those dates in ordinary cells outside the table if that layout is acceptable.

## Run the complete example

Requires the .NET 10 SDK. The project pins ClosedXML 0.105.1. From this directory:

```sh
dotnet run -- ./output
```

Choose a directory where neither output filename exists. The example refuses to overwrite either file and leaves unrelated directory contents alone. Use a new directory name for another run.

The example writes two workbooks:

- `output/monthly-sales.xlsx` contains the table below, including an average totals row.
- `output/monthly-sales-updated.xlsx` reopens the first workbook, changes Cake's January value from 7 to 10 and saves a separate copy. The original file's hash is checked before and after this operation.

| All we want is cake! | Jan 2023 | Feb 2023 | Mar 2023 |
| --- | ---: | ---: | ---: |
| Cake | 7 | 0 | 0 |
| Cheesecake | 14 | 13 | 0 |
| Waffles | 17 | 0 | 0 |
| Ø | 12.6666666666667 | 4.33333333333333 | 0 |

The updated workbook has January average `13.6666666666667`; the other columns stay the same. The averages are native `SUBTOTAL` formulas, with results evaluated before saving. The table retains its filter, field names and totals through the second save.

`TableWithData` is the table's internal name. It has no spaces; the displayed field names such as `Jan 2023` can contain spaces. Set field names before configuring the totals row.

## Verify the saved files

With Python 3 available:

```sh
python3 verify.py
```

This runs the actual .NET example in a temporary directory, then independently inspects both ZIP/XML workbooks for the exact field names, header text types, original data, table/filter range, totals formulas and their cached results. It also checks that either existing filename and a repeated run are rejected without changing existing content. An optional first argument selects a different `dotnet` executable.

The example was exercised with .NET 10.0.402 and ClosedXML 0.105.1, including a second save after changing a value. Excel's GUI was not exercised. This demonstrates text month labels in table headers; it does not make those headers date-valued cells or change ClosedXML's behavior.

References: [ClosedXML table headers and fields](https://docs.closedxml.io/en/latest/features/tables.html#header-fields), [formula calculation](https://docs.closedxml.io/en/latest/concepts/formula-calculation.html), [original usage question](https://github.com/ClosedXML/ClosedXML/discussions/2865).

## Optional coffee

This example is free. If it saves you time, a small coffee is welcome and entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
