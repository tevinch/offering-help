using System.Text.Json;
using CsvRuntimeMap;

if (args.Length != 2)
{
    Console.Error.WriteLine("Usage: CsvRuntimeMap <aliases.db> <input.csv>");
    return 2;
}

try
{
    var catalog = AliasCatalog.Load(args[0]);
    var records = CsvImport.Read(args[1], catalog);
    // Materialize and serialize before writing, so a late bad row emits no partial result.
    var json = JsonSerializer.Serialize(records);
    Console.WriteLine(json);
    return 0;
}
catch (Exception error)
{
    Console.Error.WriteLine($"{error.GetType().Name}: {error.Message}");
    return 1;
}
