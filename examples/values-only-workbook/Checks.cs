using ClosedXML.Excel;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Xml.Linq;

static class Checks
{
    private static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }

    private static void Reject(Action action, string message)
    {
        try { action(); }
        catch { return; }
        throw new InvalidOperationException(message);
    }

    public static void Run(string directory)
    {
        Require(!Directory.Exists(directory) && !File.Exists(directory), "Use a new check directory.");
        Directory.CreateDirectory(directory);
        string PathTo(string name) => Path.Combine(directory, name);
        var input = PathTo("formulas.xlsx");
        using (var workbook = new XLWorkbook())
        {
            var source = workbook.AddWorksheet("Inputs");
            source.Cell("A1").Value = 10;
            source.Cell("A2").Value = 5;
            source.Cell("A3").Value = new DateTime(2026, 10, 27);
            source.Cell("A3").Style.DateFormat.Format = "yyyy-mm-dd";
            source.Cell("B1").Value = "world";
            source.Range("D1:E1").Merge().Value = "keep this note";
            var summary = workbook.AddWorksheet("Summary");
            summary.Cell("A1").FormulaA1 = "Inputs!A1*2";
            summary.Cell("A2").FormulaA1 = "A1+Inputs!A2";
            summary.Cell("A3").FormulaA1 = "SUM(Inputs!A1:A2)";
            summary.Cell("A4").FormulaA1 = "\"hello \"&Inputs!B1";
            summary.Cell("A5").FormulaA1 = "Inputs!A1>Inputs!A2";
            summary.Cell("A6").FormulaA1 = "Inputs!A3+1";
            summary.Cell("A6").Style.DateFormat.Format = "yyyy-mm-dd";
            summary.Cell("A1").Style.Font.Bold = true;
            summary.Cell("C1").Value = "literal";
            workbook.SaveAs(input);
        }
        // Simulate a file with stale cached numbers. A cache-only export would
        // silently copy 999 instead of the current formula results.
        using (var zip = ZipFile.Open(input, ZipArchiveMode.Update))
        {
            var entry = zip.GetEntry("xl/worksheets/sheet2.xml")!;
            XDocument xml;
            using (var stream = entry.Open()) xml = XDocument.Load(stream);
            XNamespace ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
            foreach (var cell in xml.Descendants(ns + "c").Where(c => c.Element(ns + "f") is not null))
            {
                cell.Attribute("t")?.Remove();
                cell.SetElementValue(ns + "v", 999);
            }
            entry.Delete();
            using var replacement = zip.CreateEntry("xl/worksheets/sheet2.xml").Open();
            xml.Save(replacement);
        }
        var before = SHA256.HashData(File.ReadAllBytes(input));
        using (var original = new XLWorkbook(input))
            Require(original.Worksheet("Summary").CellsUsed().Count(c => c.HasFormula) == 6, "The input must contain six real formulas.");

        foreach (var name in new[] { "values.xlsx", "values-again.xlsx" })
        {
            var output = PathTo(name);
            ValuesOnly.Export(input, output);
            using var saved = new XLWorkbook(output);
            Require(saved.Worksheets.SelectMany(w => w.CellsUsed()).All(c => !c.HasFormula), "Export still contains formulas.");
            var summary = saved.Worksheet("Summary");
            Require(summary.Cell("A1").GetDouble() == 20 && summary.Cell("A2").GetDouble() == 25 && summary.Cell("A3").GetDouble() == 15, "Dependent numeric formula results changed.");
            Require(summary.Cell("A4").GetString() == "hello world", "Text result changed.");
            Require(summary.Cell("A5").GetBoolean(), "Boolean result changed.");
            Require(summary.Cell("A6").GetFormattedString() == "2026-10-28", "Date result or date format changed.");
            Require(summary.Cell("A1").Style.Font.Bold && summary.Cell("C1").GetString() == "literal", "Existing style or literal changed.");
            var source = saved.Worksheet("Inputs");
            Require(source.Cell("A3").GetDateTime() == new DateTime(2026, 10, 27), "Original date changed.");
            Require(source.MergedRanges.Count == 1 && source.Cell("D1").GetString() == "keep this note" && source.Cell("F1").IsEmpty(), "Existing merged/blank content changed.");
            using var zip = ZipFile.OpenRead(output);
            XNamespace ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
            foreach (var sheet in zip.Entries.Where(e => e.FullName.StartsWith("xl/worksheets/sheet") && e.FullName.EndsWith(".xml")))
            {
                using var stream = sheet.Open();
                Require(!XDocument.Load(stream).Descendants(ns + "f").Any(), "Serialized worksheet still has formula elements.");
            }
        }
        Require(before.SequenceEqual(SHA256.HashData(File.ReadAllBytes(input))), "Input file bytes changed.");
        var sentinel = PathTo("existing.xlsx");
        File.WriteAllText(sentinel, "keep existing output");
        Reject(() => ValuesOnly.Export(input, sentinel), "An existing output was overwritten.");
        Require(File.ReadAllText(sentinel) == "keep existing output", "Existing output bytes changed.");
        Reject(() => ValuesOnly.Export(input, input), "The source path was accepted as output.");
        Require(before.SequenceEqual(SHA256.HashData(File.ReadAllBytes(input))), "Collision check changed source.");

        foreach (var kind in new[] { "error", "cycle", "unsupported", "array", "table" })
        {
            var problemInput = PathTo(kind + ".xlsx");
            var problemOutput = PathTo(kind + "-values.xlsx");
            using (var workbook = new XLWorkbook())
            {
                var sheet = workbook.AddWorksheet("Data");
                sheet.Cell("A1").Value = 1;
                switch (kind)
                {
                    case "error": sheet.Cell("B1").FormulaA1 = "1/0"; break;
                    case "cycle": sheet.Cell("B1").FormulaA1 = "B1+1"; break;
                    case "unsupported": sheet.Cell("B1").FormulaA1 = "NOT_A_WORKBOOK_FUNCTION(A1)"; break;
                    case "array": sheet.Range("B1:B2").FormulaArrayA1 = "A1:A2*2"; break;
                    case "table":
                        sheet.Cell("A1").Value = "Quantity";
                        sheet.Cell("B1").Value = "Double";
                        sheet.Cell("A2").Value = 2;
                        sheet.Cell("B2").FormulaA1 = "A2*2";
                        sheet.Range("A1:B2").CreateTable("Items");
                        break;
                }
                workbook.SaveAs(problemInput);
            }
            var originalHash = SHA256.HashData(File.ReadAllBytes(problemInput));
            Reject(() => ValuesOnly.Export(problemInput, problemOutput), $"The {kind} case should stop before saving.");
            Require(!File.Exists(problemOutput), $"The {kind} case wrote an output.");
            Require(originalHash.SequenceEqual(SHA256.HashData(File.ReadAllBytes(problemInput))), $"The {kind} input changed.");
        }
        Console.WriteLine("PASS: two real file exports, six typed formula results, unchanged content/source, no serialized formulas, and seven refusal cases.");
    }
}
