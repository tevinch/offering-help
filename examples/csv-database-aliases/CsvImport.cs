using System.Globalization;
using System.Text;
using CsvHelper;
using CsvHelper.Configuration;

namespace CsvRuntimeMap;

public static class CsvImport
{
    public static List<ImportRecord> Read(string csvPath, AliasCatalog catalog)
    {
        // Keep native header, missing-field and bad-data validation enabled.
        var configuration = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            ExceptionMessagesContainRawData = false,
        };
        using var input = new StreamReader(csvPath, new UTF8Encoding(false, true), detectEncodingFromByteOrderMarks: true);
        using var csv = new CsvReader(input, configuration);
        csv.Context.RegisterClassMap(new ImportRecordMap(catalog));
        if (!csv.Read())
            throw new InvalidDataException("The CSV file has no header.");
        csv.ReadHeader();
        csv.ValidateHeader<ImportRecord>();
        catalog.ValidateUnambiguousHeader(csv.HeaderRecord!);
        var records = new List<ImportRecord>();
        while (csv.Read())
            records.Add(csv.GetRecord<ImportRecord>());
        return records;
    }

    private sealed class ImportRecordMap : ClassMap<ImportRecord>
    {
        public ImportRecordMap(AliasCatalog catalog)
        {
            Map(record => record.EventId).Name(catalog.NamesFor(nameof(ImportRecord.EventId)));
            Map(record => record.Period).Name(catalog.NamesFor(nameof(ImportRecord.Period)));
            Map(record => record.MeanLossAmount).Name(catalog.NamesFor(nameof(ImportRecord.MeanLossAmount)));
            Map(record => record.DayInPeriod).Name(catalog.NamesFor(nameof(ImportRecord.DayInPeriod)));
            Map(record => record.PerilZone).Name(catalog.NamesFor(nameof(ImportRecord.PerilZone)));
            Map(record => record.CatalogueTypeCode).Name(catalog.NamesFor(nameof(ImportRecord.CatalogueTypeCode)));
        }
    }
}
