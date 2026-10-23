using System.Text.Json;
using AsyncDataReader;
using Csla;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;

var connectionString = Environment.GetEnvironmentVariable("READER_CONNECTION_STRING");
if (string.IsNullOrWhiteSpace(connectionString))
{
    Console.Error.WriteLine("Set READER_CONNECTION_STRING to a PostgreSQL connection string. See README.md.");
    return 2;
}

try
{
    await using var dataSource = NpgsqlDataSource.Create(connectionString);
    await using var services = ExampleServices.Create(dataSource);
    await using var scope = services.CreateAsyncScope();
    var portal = scope.ServiceProvider.GetRequiredService<IDataPortal<PersonList>>();
    var people = await portal.FetchAsync(args.Length == 0 ? "" : args[0]);
    Console.WriteLine(JsonSerializer.Serialize(people.Select(p => new PersonRow(p.Id, p.Name, p.Nickname))));
    return 0;
}
catch (Exception)
{
    // Avoid printing a connection string or provider diagnostics to an ordinary CLI user.
    Console.Error.WriteLine("Fetch failed. Check the connection and the person_directory schema.");
    return 1;
}
