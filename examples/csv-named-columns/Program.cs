using NamedInventory;
using System.Text.Json;

if (args.Length != 1)
{
    Console.Error.WriteLine("Usage: dotnet run --project Inventory.csproj -- <file.csv>");
    return 2;
}

try
{
    using var input = new StreamReader(args[0]);
    Console.WriteLine(JsonSerializer.Serialize(InventoryReader.Read(input),
        new JsonSerializerOptions { WriteIndented = true }));
    return 0;
}
catch (Exception error) when (error is CsvHelper.CsvHelperException or IOException)
{
    Console.Error.WriteLine($"{error.GetType().Name}: {error.Message}");
    return 1;
}
