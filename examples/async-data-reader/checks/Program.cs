using System.Diagnostics;
using AsyncDataReader;
using Csla;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;

var connectionString = Environment.GetEnvironmentVariable("READER_CONNECTION_STRING")
    ?? throw new InvalidOperationException("Run through validate.py.");
await using var observer = NpgsqlDataSource.Create(connectionString);

void Require(bool condition, string message)
{
    if (!condition) throw new InvalidOperationException(message);
}

PersonRow[] Snapshot(PersonList people) => people
    .Select(p => new PersonRow(p.Id, p.Name, p.Nickname)).ToArray();

void Exact(IEnumerable<PersonRow> actual, params PersonRow[] expected) =>
    Require(actual.SequenceEqual(expected), "Final caller-visible rows differ from literal fixture.");

async Task<bool> IsSleeping(string applicationName)
{
    await using var command = observer.CreateCommand("""
        SELECT EXISTS (
            SELECT 1 FROM pg_stat_activity
            WHERE application_name = $1 AND state = 'active'
              AND wait_event = 'PgSleep' AND query LIKE '%FROM person_directory%'
        )
        """);
    command.Parameters.AddWithValue(applicationName);
    return (bool)(await command.ExecuteScalarAsync())!;
}

async Task ObserveSleep(string applicationName)
{
    var timeout = Stopwatch.StartNew();
    while (timeout.Elapsed < TimeSpan.FromSeconds(2))
    {
        if (await IsSleeping(applicationName)) return;
        await Task.Delay(20);
    }
    throw new InvalidOperationException("Expected provider query was not independently observed in PgSleep.");
}

NpgsqlDataSource Source(string applicationName, int delaySeconds = 0)
{
    var settings = new NpgsqlConnectionStringBuilder(connectionString)
    {
        ApplicationName = applicationName,
        Options = $"-c reader_test.delay_seconds={delaySeconds}"
    };
    return NpgsqlDataSource.Create(settings.ConnectionString);
}

async Task Pending<T>(Func<Task<T>> start, string applicationName)
{
    var elapsed = Stopwatch.StartNew();
    var pending = start();
    Require(elapsed.Elapsed < TimeSpan.FromSeconds(1),
        "Starting the fetch blocked the caller during provider IO.");
    await ObserveSleep(applicationName);
    Require(!pending.IsCompleted, "Fetch completed before provider results were available.");
    var heartbeats = 0;
    for (var i = 0; i < 3; i++)
    {
        await Task.Delay(20);
        heartbeats++;
    }
    Require(heartbeats == 3 && !pending.IsCompleted,
        "Caller could not continue while the delayed provider query was pending.");
    var result = await pending.WaitAsync(TimeSpan.FromSeconds(8));
    var rows = result switch
    {
        PersonList people => Snapshot(people),
        IReadOnlyList<PersonRow> people => people.ToArray(),
        _ => throw new InvalidOperationException("Unexpected result type.")
    };
    Exact(rows, new PersonRow(1, "Ada Lovelace", null));
    Require(!await IsSleeping(applicationName), "Provider query still runs after fetch completed.");
    Console.WriteLine($"PASS {applicationName}: observed PgSleep; caller continued; exact result returned");
}

// A synchronous DAL would look responsive behind the console local portal's
// internal scheduling. Test native DAL behavior directly before testing CSLA.
await using (var directSource = Source("reader-direct", 3))
{
    var dal = new PersonDal(directSource);
    await Pending(() => dal.FetchAsync("Ada"), "reader-direct");
}

await using var dataSource = Source("reader-normal");
await using var services = ExampleServices.Create(dataSource);
await using var scope = services.CreateAsyncScope();
var portal = scope.ServiceProvider.GetRequiredService<IDataPortal<PersonList>>();

Exact(Snapshot(await portal.FetchAsync("Missing")));
Exact(Snapshot(await portal.FetchAsync("Ada")), new PersonRow(1, "Ada Lovelace", null));
Exact(Snapshot(await portal.FetchAsync("")),
    new PersonRow(1, "Ada Lovelace", null), new PersonRow(2, "Grace Hopper", "Amazing Grace"),
    new PersonRow(3, "José García", ""));
// Input is data, not SQL. A dropped parameter would make this fail.
Exact(Snapshot(await portal.FetchAsync("' OR true --")));
Console.WriteLine("PASS CSLA zero/one/multiple rows, Unicode, DBNull, empty string, parameter input");

await using (var delayedSource = Source("reader-portal", 3))
await using (var delayedServices = ExampleServices.Create(delayedSource))
await using (var delayedScope = delayedServices.CreateAsyncScope())
{
    var delayedPortal = delayedScope.ServiceProvider.GetRequiredService<IDataPortal<PersonList>>();
    await Pending(() => delayedPortal.FetchAsync("Ada"), "reader-portal");
}

// A real PostgreSQL error must escape CSLA, and a later fetch must still work.
await using (var rename = observer.CreateCommand("ALTER VIEW person_directory RENAME TO hidden_directory"))
    await rename.ExecuteNonQueryAsync();
try
{
    Exception? error = null;
    try { await portal.FetchAsync("Ada"); }
    catch (Exception ex) { error = ex; }
    var found = false;
    for (var current = error; current != null; current = current.InnerException)
        if (current is PostgresException { SqlState: "42P01" }) found = true;
    Require(found, "Expected missing-relation provider error did not reach caller.");
}
finally
{
    await using var restore = observer.CreateCommand("ALTER VIEW hidden_directory RENAME TO person_directory");
    await restore.ExecuteNonQueryAsync();
}
Exact(Snapshot(await portal.FetchAsync("Grace")), new PersonRow(2, "Grace Hopper", "Amazing Grace"));
Console.WriteLine("PASS provider error propagated through CSLA; later fetch returned complete result");

// This is DAL cancellation only. The token is not a data portal criterion.
await using (var cancelSource = Source("reader-cancel", 5))
{
    var dal = new PersonDal(cancelSource);
    using var cancellation = new CancellationTokenSource();
    var pending = dal.FetchAsync("Ada", cancellation.Token);
    await ObserveSleep("reader-cancel");
    cancellation.Cancel();
    var canceled = false;
    try { await pending.WaitAsync(TimeSpan.FromSeconds(2)); }
    catch (OperationCanceledException) { canceled = true; }
    Require(canceled, "Cancellation did not reach the active provider operation.");
    Require(!await IsSleeping("reader-cancel"), "Canceled provider query is still running.");
    // Use this same data source after cancellation (with its new per-call connection).
    Exact(await dal.FetchAsync("Ada"), new PersonRow(1, "Ada Lovelace", null));
    Console.WriteLine("PASS DAL token canceled active provider query; same source handled later fetch");
}

await using (var unchanged = observer.CreateCommand("""
    SELECT jsonb_agg(to_jsonb(p) ORDER BY id)::text FROM person_seed p
    """))
{
    var snapshot = (string)(await unchanged.ExecuteScalarAsync())!;
    var expected = """
        [{"id":1,"name":"Ada Lovelace","nickname":null},
         {"id":2,"name":"Grace Hopper","nickname":"Amazing Grace"},
         {"id":3,"name":"José García","nickname":""}]
        """;
    Require(System.Text.Json.Nodes.JsonNode.DeepEquals(
        System.Text.Json.Nodes.JsonNode.Parse(snapshot), System.Text.Json.Nodes.JsonNode.Parse(expected)),
        "Existing source rows changed.");
}
await using (var sentinel = observer.CreateCommand("SELECT note FROM existing_sentinel WHERE id = 77"))
    Require((string)(await sentinel.ExecuteScalarAsync())! == "keep this value", "Existing sentinel changed.");
Console.WriteLine("PASS existing rows and sentinel unchanged");
