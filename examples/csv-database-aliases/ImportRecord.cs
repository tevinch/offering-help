namespace CsvRuntimeMap;

public sealed class ImportRecord
{
    public string EventId { get; set; } = "";
    public string Period { get; set; } = "";
    public decimal MeanLossAmount { get; set; }
    public string DayInPeriod { get; set; } = "";
    public string PerilZone { get; set; } = "";
    public string CatalogueTypeCode { get; set; } = "";
}
