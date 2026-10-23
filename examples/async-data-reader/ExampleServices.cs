using Csla.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;

namespace AsyncDataReader;

public static class ExampleServices
{
    public static ServiceProvider Create(NpgsqlDataSource dataSource)
    {
        var services = new ServiceCollection();
        services.AddCsla(options => options.AddConsoleApp());
        // The caller owns the shared, thread-safe pool. Each DAL call owns a connection.
        services.AddSingleton(dataSource);
        services.AddTransient<IPersonDal, PersonDal>();
        return services.BuildServiceProvider(validateScopes: true);
    }
}
