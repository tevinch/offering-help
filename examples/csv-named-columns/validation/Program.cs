using CsvHelper;
using CsvHelper.Configuration;
using NamedInventory;
using System.Globalization;
using System.Text.Json;

static void Check(bool condition, string message)
{
    if (!condition) throw new InvalidOperationException(message);
}

static List<InventoryItem> Read(string text) => InventoryReader.Read(new StringReader(text));

static void Reject<T>(string text) where T : Exception
{
    try { Read(text); }
    catch (T) { return; }
    throw new InvalidOperationException($"Expected {typeof(T).Name}");
}

var original = File.ReadAllText(args[0]);
var widths = new List<int>();
int? headerWidth = null;
var originalConfig = new CsvConfiguration(CultureInfo.InvariantCulture)
{
    ShouldSkipRecord = args =>
    {
        var width = args.Row.Parser.Count;
        widths.Add(width);
        headerWidth ??= width;
        return width < headerWidth;
    }
};
using (var baseline = new CsvReader(new StringReader(original), originalConfig))
{
    var records = baseline.GetRecords<InventoryItem>().ToList();
    Check(widths.SequenceEqual(new[] { 9, 5, 5 }), "Original filter must inspect header and both rows");
    Check(records.Count == 0, "Original filter should reproduce the zero-record result");
    Console.WriteLine(JsonSerializer.Serialize(new { originalFilterWidths = widths, originalRecords = records.Count }));
}

var items = Read(original);
Check(items.Count == 2, $"Expected both original inventory records, got {items.Count}");
foreach (var item in items)
{
    Check(item.ProductCode == "1231234123123-123123123", "ProductCode");
    Check(item.Brand == "Item Wheel Components", "Brand");
    Check(item.Description == "28 CHROME MOD *NO RIVETS 1x4 5x114.3 CHROME  ", "Description must retain trailing spaces");
    Check(item.Stock == "0" && item.StockOther == "0", "Both stocks");
}

var reordered = Read("StockOther,Description,Brand,ProductCode,Stock,,\n8,\"Wheel, \"\"chrome\"\"\nsecond line\",Components,P-2,3\n").Single();
Check(reordered.ProductCode == "P-2" && reordered.Brand == "Components" && reordered.Stock == "3" && reordered.StockOther == "8", "Map by names after column reorder");
Check(reordered.Description == "Wheel, \"chrome\"\nsecond line", "RFC4180 comma, escaped quotes and newline");

const string header = "ProductCode,Brand,Description,Stock,StockOther\n";
var blank = Read(header + "\nP-3,,,0,\n").Single();
Check(blank.Brand == "" && blank.Description == "" && blank.StockOther == "", "Empty cells are valid strings; blank lines remain ignored");
Check(Read(header + "P-4,B,D,1,2,extra\n").Single().StockOther == "2", "Unmapped trailing columns do not shift required fields");

Reject<HeaderValidationException>("ProductCode,Brand,Description,Stock\nP,B,D,0\n");
Reject<CsvHelper.MissingFieldException>(header + "P,B,D,0\n");
Reject<BadDataException>(header + "P,B,\"broken\"tail,0,0\n");
Check(Read(original).Count == 2, "A repeated complete read must still return both records");
Console.WriteLine("PASS: original rows, names, quoted fields, empty cells, validation errors, repeated reads");
