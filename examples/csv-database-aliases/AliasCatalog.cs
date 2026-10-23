using Microsoft.Data.Sqlite;

namespace CsvRuntimeMap;

public sealed class AliasCatalog
{
    // Metadata can name these existing members; it cannot change the model's types.
    private static readonly Dictionary<string, string> ExpectedTypes = new(StringComparer.Ordinal)
    {
        [nameof(ImportRecord.EventId)] = "String",
        [nameof(ImportRecord.Period)] = "String",
        [nameof(ImportRecord.MeanLossAmount)] = "Decimal",
        [nameof(ImportRecord.DayInPeriod)] = "String",
        [nameof(ImportRecord.PerilZone)] = "String",
        [nameof(ImportRecord.CatalogueTypeCode)] = "String",
    };

    private readonly Dictionary<string, string[]> aliases;

    private AliasCatalog(Dictionary<string, string[]> aliases) => this.aliases = aliases;

    public string[] NamesFor(string property) => (string[])aliases[property].Clone();

    public static AliasCatalog Load(string databasePath)
    {
        var connectionString = new SqliteConnectionStringBuilder
        {
            DataSource = databasePath,
            Mode = SqliteOpenMode.ReadOnly,
        }.ToString();
        using var connection = new SqliteConnection(connectionString);
        connection.Open();
        using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT CsvColumnName, PropertyName, DataType
            FROM CsvColumnMappings
            ORDER BY PropertyName, CsvColumnName
            """;
        using var reader = command.ExecuteReader();
        var grouped = new Dictionary<string, List<string>>(StringComparer.Ordinal);
        var owners = new Dictionary<string, string>(StringComparer.Ordinal);
        while (reader.Read())
        {
            if (reader.IsDBNull(0) || reader.IsDBNull(1) || reader.IsDBNull(2))
                throw new InvalidDataException("Mapping names, properties and data types cannot be SQL NULL.");
            var name = reader.GetString(0);
            var property = reader.GetString(1);
            var dataType = reader.GetString(2);
            if (string.IsNullOrWhiteSpace(name))
                throw new InvalidDataException("CSV aliases cannot be empty or whitespace.");
            if (!ExpectedTypes.TryGetValue(property, out var expectedType))
                throw new InvalidDataException($"Unknown mapped property '{property}'.");
            if (!string.Equals(dataType, expectedType, StringComparison.Ordinal))
                throw new InvalidDataException($"Property '{property}' requires DataType '{expectedType}', not '{dataType}'.");
            if (owners.TryGetValue(name, out var existingOwner))
            {
                if (existingOwner != property)
                    throw new InvalidDataException($"CSV alias '{name}' belongs to more than one property.");
                continue; // Repeated identical metadata does not change the alias set.
            }
            owners.Add(name, property);
            if (!grouped.TryGetValue(property, out var names))
                grouped.Add(property, names = []);
            names.Add(name);
        }

        foreach (var property in ExpectedTypes.Keys)
            if (!grouped.ContainsKey(property))
                throw new InvalidDataException($"No aliases configured for required property '{property}'.");
        return new AliasCatalog(grouped.ToDictionary(pair => pair.Key, pair => pair.Value.ToArray(), StringComparer.Ordinal));
    }

    public void ValidateUnambiguousHeader(string[] header)
    {
        foreach (var (property, names) in aliases)
        {
            // Count positions, so a repeated identical header is also rejected.
            var matchingColumns = header.Count(name => names.Contains(name, StringComparer.Ordinal));
            if (matchingColumns > 1)
                throw new InvalidDataException($"CSV has more than one column mapped to '{property}'. Supply one of its aliases.");
        }
    }
}
