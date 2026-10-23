using Npgsql;

namespace AsyncDataReader;

public sealed record PersonRow(int Id, string? Name, string? Nickname);

public interface IPersonDal
{
    Task<IReadOnlyList<PersonRow>> FetchAsync(string prefix, CancellationToken cancellationToken = default);
}

public sealed class PersonDal(NpgsqlDataSource dataSource) : IPersonDal
{
    public async Task<IReadOnlyList<PersonRow>> FetchAsync(string prefix, CancellationToken cancellationToken = default)
    {
        await using var connection = await dataSource.OpenConnectionAsync(cancellationToken);
        await using var command = new NpgsqlCommand(
            "SELECT id, name, nickname FROM person_directory WHERE starts_with(name, $1) ORDER BY id", connection);
        command.Parameters.AddWithValue(prefix);
        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        var rows = new List<PersonRow>();
        while (await reader.ReadAsync(cancellationToken))
            rows.Add(new(reader.GetInt32(0), reader.GetString(1),
                reader.IsDBNull(2) ? null : reader.GetString(2)));
        return rows;
    }
}
