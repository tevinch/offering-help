using CsvHelper;
using CsvHelper.Configuration;
using System.Globalization;

namespace NamedInventory;

public sealed class InventoryItem
{
    public string ProductCode { get; set; } = "";
    public string Brand { get; set; } = "";
    public string Description { get; set; } = "";
    public string Stock { get; set; } = "";
    public string StockOther { get; set; } = "";
}

public static class InventoryReader
{
    public static List<InventoryItem> Read(TextReader input)
    {
        // Leave header, missing-field and malformed-data validation enabled.
        var config = new CsvConfiguration(CultureInfo.InvariantCulture);
        using var csv = new CsvReader(input, config, leaveOpen: true);
        csv.Context.RegisterClassMap<InventoryMap>();
        return csv.GetRecords<InventoryItem>().ToList();
    }
}

public sealed class InventoryMap : ClassMap<InventoryItem>
{
    public InventoryMap()
    {
        Map(item => item.ProductCode).Name("ProductCode");
        Map(item => item.Brand).Name("Brand");
        Map(item => item.Description).Name("Description");
        Map(item => item.Stock).Name("Stock");
        Map(item => item.StockOther).Name("StockOther");
    }
}
