using ClosedXML.Excel;

try
{
    if (args.Length == 2 && args[0] == "--check")
    {
        Checks.Run(args[1]);
    }
    else if (args.Length == 2)
    {
        ValuesOnly.Export(args[0], args[1]);
        Console.WriteLine("Saved a new values-only workbook.");
    }
    else
    {
        Console.Error.WriteLine("Usage: dotnet run -- input.xlsx output.xlsx\n       dotnet run -- --check new-check-directory");
        return 2;
    }
    return 0;
}
catch (Exception error)
{
    Console.Error.WriteLine($"Export stopped: {error.Message}");
    return 1;
}

static class ValuesOnly
{
    public static void Export(string input, string output)
    {
        if (Path.GetFullPath(input).Equals(Path.GetFullPath(output), StringComparison.OrdinalIgnoreCase))
            throw new ArgumentException("Choose a different output path.");
        if (File.Exists(output) || Directory.Exists(output))
            throw new IOException("Output already exists; choose a new path.");

        using var workbook = new XLWorkbook(input);
        var formulas = workbook.Worksheets.SelectMany(w => w.CellsUsed())
            .Where(c => c.HasFormula).ToList();
        if (formulas.Any(c => c.HasArrayFormula || c.FormulaReference is not null))
            throw new NotSupportedException("This recipe accepts ordinary scalar formulas, not array or data-table formulas.");
        if (workbook.Worksheets.SelectMany(w => w.Tables)
            .Any(t => t.CellsUsed().Any(c => c.HasFormula)))
            throw new NotSupportedException("This recipe does not flatten formula-bearing Excel tables.");

        workbook.RecalculateAllFormulas();
        // Snapshot everything before changing cells that other formulas depend on.
        var values = formulas.Select(c => (Cell: c, Value: c.Value)).ToList();
        if (values.Any(v => v.Value.Type == XLDataType.Error))
            throw new InvalidOperationException("A formula calculated to an error; no output was saved.");
        foreach (var item in values)
            item.Cell.Value = item.Value; // The native setter also clears the formula.

        if (workbook.Worksheets.SelectMany(w => w.CellsUsed()).Any(c => c.HasFormula))
            throw new InvalidOperationException("Some cell formulas remain; no output was saved.");

        // Finish serialization before creating the destination. CreateNew also
        // refuses a file that appears after the earlier existence check.
        using var bytes = new MemoryStream();
        workbook.SaveAs(bytes);
        bytes.Position = 0;
        using var file = new FileStream(output, FileMode.CreateNew, FileAccess.Write);
        bytes.CopyTo(file);
    }
}
