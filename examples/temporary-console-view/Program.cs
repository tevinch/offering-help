using Spectre.Console;

var console = AnsiConsole.Console;
console.WriteLine("Existing report: 42 items.");
console.WriteLine("This main-screen content should remain after each view.");

var unavailable = TemporaryView.GetUnavailableReason(console);
if (unavailable is not null)
{
    console.WriteLine($"View unavailable: {unavailable}");
    return 2;
}

for (var round = 1; round <= 2; round++)
{
    console.WriteLine($"Enter opens view {round}.");
    if (System.Console.ReadLine() is null)
    {
        return 2;
    }

    try
    {
        var selected = TemporaryView.Choose(console);
        // This runs after the alternate buffer has been left.
        console.WriteLine($"Returned {round}: {selected}");
    }
    catch (NotSupportedException error)
    {
        console.WriteLine($"View unavailable: {error.Message}");
        return 2;
    }
}

console.WriteLine("Finished both selections.");
return 0;
