using ClosedXML.Excel;
using System.Globalization;
using System.Security.Cryptography;

var output = args.Length == 0 ? Directory.GetCurrentDirectory() : Path.GetFullPath(args[0]);
var original = Path.Combine(output, "monthly-sales.xlsx");
var updated = Path.Combine(output, "monthly-sales-updated.xlsx");
if (Path.Exists(original) || Path.Exists(updated))
{
    Console.Error.WriteLine("Choose an output directory without monthly-sales.xlsx or monthly-sales-updated.xlsx.");
    Environment.ExitCode = 1;
    return;
}
Directory.CreateDirectory(output);
using (var workbook = new XLWorkbook())
{
    var sheet = workbook.AddWorksheet("Monthly sales");
    object[][] data = [["Cake", 7, 0, 0], ["Cheesecake", 14, 13, 0], ["Waffles", 17, 0, 0]];
    var table = sheet.Cell("A1").InsertTable(data, "TableWithData", true);
    table.Field(0).Name = "All we want is cake!";
    for (var month = 0; month < 3; month++)
    {
        var date = new DateOnly(2023, month + 1, 1);
        table.Field(month + 1).Name = date.ToString("MMM yyyy", CultureInfo.GetCultureInfo("en-US"));
    }
    table.ShowTotalsRow = true;
    table.Field(0).TotalsRowLabel = "Ø";
    for (var month = 1; month <= 3; month++)
        table.Field(month).TotalsRowFunction = XLTotalsRowFunction.Average;
    sheet.ColumnWidth = 24;
    workbook.SaveAs(original, new SaveOptions { EvaluateFormulasBeforeSaving = true });
}
var originalHash = SHA256.HashData(File.ReadAllBytes(original));
using (var workbook = new XLWorkbook(original))
{
    workbook.Worksheet(1).Cell("B2").Value = 10;
    workbook.SaveAs(updated, new SaveOptions { EvaluateFormulasBeforeSaving = true });
}
if (!originalHash.SequenceEqual(SHA256.HashData(File.ReadAllBytes(original))))
    throw new InvalidOperationException("The original workbook changed during the separate save.");
Console.WriteLine($"Wrote {original}");
Console.WriteLine($"Wrote {updated}");
Console.WriteLine($"Original SHA256: {Convert.ToHexString(originalHash)}");
