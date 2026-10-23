using Spectre.Console;

public static class TemporaryView
{
    public static string? GetUnavailableReason(IAnsiConsole console)
    {
        if (System.Console.IsInputRedirected || System.Console.IsOutputRedirected || !console.Profile.Out.IsTerminal)
        {
            return "use an interactive terminal with input and output attached.";
        }

        var capabilities = console.Profile.Capabilities;
        if (!capabilities.Ansi || !capabilities.Interactive || !capabilities.AlternateBuffer)
        {
            return "this terminal does not report interactive ANSI and alternate-buffer support.";
        }

        if (console.Profile.Width < 60 || console.Profile.Height < 18)
        {
            return "this fixed view needs at least 60 columns and 18 rows.";
        }

        return null;
    }

    public static string Choose(IAnsiConsole console)
    {
        var unavailable = GetUnavailableReason(console);
        if (unavailable is not null)
        {
            throw new NotSupportedException(unavailable);
        }

        string? selected = null;
        console.AlternateScreen(() =>
        {
            // Static content uses only a few rows; it is not a live display.
            var widgets = new Grid()
                .AddColumn(new GridColumn().Width(26))
                .AddColumn(new GridColumn().Width(26));
            widgets.AddRow(
                new Panel(new Text("Project: demo\nMode: preview")).Header("Context widget").Expand(),
                new Panel(new Text("Items: 42\nReady to choose")).Header("Summary widget").Expand());
            console.Write(widgets);
            console.WriteLine();

            selected = console.Prompt(new SelectionPrompt<string>()
                .Title("Choose a destination")
                .PageSize(3)
                .AddChoices("Alpha", "Beta", "Gamma"));
        });

        return selected ?? throw new InvalidOperationException("The view completed without a selection.");
    }
}
