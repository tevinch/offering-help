# Read inventory CSV by column name

A header can contain unused trailing columns while each data row contains all five fields you need. CsvHelper can still map those fields by name; the data rows do not need to be padded to the header's total width.

This runnable example addresses the input in [CsvHelper discussion #2252](https://github.com/JoshClose/CsvHelper/discussions/2252), using CsvHelper **33.1.0** and .NET 10. It returns both inventory records, keeps quoted text intact and continues to reject missing required fields and malformed CSV.

## Why the original reader returns zero records

The sample header has **9** fields, including four unused empty names. Each data row has **5** fields. The original `ShouldSkipRecord` compares every record with the header width:

```csharp
return args.Row.Parser.Record.Length < headerCount;
```

Both valid data rows satisfy `5 < 9`, so both are skipped. Changing quote or escape mode does not address that filter.

Remove that width-based `ShouldSkipRecord` callback. Keep the five `.Name(...)` mappings and CsvHelper's default RFC4180 quoting and validation:

```csharp
var config = new CsvConfiguration(CultureInfo.InvariantCulture);
using var csv = new CsvReader(input, config, leaveOpen: true);
csv.Context.RegisterClassMap<InventoryMap>();
var inventories = csv.GetRecords<InventoryItem>().ToList();
```

[InventoryReader.cs](InventoryReader.cs) contains the complete model and map. Materializing with `ToList()` inside the reader's scope finishes reading before disposal. The caller owns `input`.

## Run

From this directory, with the .NET 10 SDK installed:

```sh
dotnet restore Inventory.csproj --locked-mode
dotnet run --project Inventory.csproj --no-restore -- inventory.csv
```

The output is a JSON array with **two** objects. Each contains the original `ProductCode`, `Brand`, `Description`, `Stock` and `StockOther`; the two spaces at the end of the description remain intact. The stock properties stay strings, matching the original model.

Pass your own UTF-8 CSV path in place of `inventory.csv`. Named mapping also permits reordering these five columns. Empty string cells are accepted; a missing required field is a different condition and remains an error.

## Validation boundaries

- Do not set `HeaderValidated`, `MissingFieldFound` or `BadDataFound` to `null` to make this input load. This example leaves them enabled.
- The default `DetectColumnCountChanges` is `false`. This accepts variable row widths when every mapped field is present. If your feed contract requires exactly the same width on every row, this particular file violates that contract; validate or correct the feed separately rather than silently changing the contract.
- Extra unnamed columns are not mapped. This example does not treat them as required inventory data or validate their business meaning.
- The CLI reads the whole file before printing JSON. A malformed later row produces an error and a nonzero exit code, without a partial JSON result. For large feeds, choose an explicit transactional or streaming error policy instead of assuming partial imports are safe.

Run the checks:

```sh
python3 validate.py
```

The checks execute the original filter and independently observe widths `[9, 5, 5]` and zero records. They then verify both complete records, reordered columns, quoted commas/quotes/newlines, empty cells, repeated reads, and errors for missing headers, missing fields and malformed quoting. The CLI checks inspect actual file-to-JSON output and confirm that later errors do not emit partial results. These are scripted checks, not confirmation from the original requester.

First-party references: [mapping by name](https://joshclose.github.io/CsvHelper/examples/configuration/class-maps/mapping-by-name/) and [reading records](https://joshclose.github.io/CsvHelper/examples/reading/get-class-records/).

## Optional coffee

The example is free. If it helps and you would like to buy me a coffee, contributions are entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
