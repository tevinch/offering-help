using SkiaSharp;
using Svg.Skia;
using TerraFluent.Chart.Reporting.Builder;
using TerraFluent.Pdf.Reporting.Core;
using TerraFluent.Pdf.Reporting.Helpers;

if (args.Length != 2 || args[0] is not ("A" or "B"))
{
    Console.Error.WriteLine("Usage: dotnet run -- A|B OUTPUT_DIRECTORY");
    return 1;
}

try
{
    string sample = args[0];
    string outputDirectory = Path.GetFullPath(args[1]);
    if (Directory.Exists(outputDirectory) && Directory.EnumerateFileSystemEntries(outputDirectory).Any())
        throw new IOException("Output directory must be new or empty. Choose another directory.");
    Directory.CreateDirectory(outputDirectory);

    string[] weeks = ["Week 1", "Week 2", "Week 3", "Week 4"];
    double[] completed = sample == "A" ? [18, 32, 24, 41] : [38, 14, 43, 22];
    double[] requests = sample == "A" ? [12, 21, 17, 29] : [31, 13, 35, 19];

    var columnChart = ChartBuilder.Create()
        .Title("Completed tasks")
        .Size(800, 450)
        .AsStatic()
        .Legend(legend => legend.AtBottom().Padding(6))
        .XAxis("Week", weeks)
        .YAxis("Tasks", min: 0, max: 50)
        .Series(series => series.AddColumn("Completed", completed))
        .ShowDataLabels();
    var lineChart = ChartBuilder.Create()
        .Title("Support requests")
        .Size(800, 450)
        .AsStatic()
        .Legend(legend => legend.AtBottom().Padding(6))
        .XAxis("Week", weeks)
        .YAxis("Requests", min: 0, max: 50)
        .Series(series => series.AddLine("Requests", requests))
        .ShowDataLabels();

    byte[] columnPng = RenderPng(columnChart, "column", outputDirectory);
    byte[] linePng = RenderPng(lineChart, "line", outputDirectory);
    string reportPath = Path.Combine(outputDirectory, "report.pdf");
    PdfDocument.Create(document => document.Page(page =>
    {
        page.Size(PageSize.A4);
        page.Margin(36);
        page.DefaultTextStyle(style => style.FontSize(10));
        page.Header().Text($"Weekly team report - sample {sample}").Bold().FontSize(20);
        page.Content().Column(col =>
        {
            col.Spacing(6);
            col.Item().Text("Synthetic sample data - four weeks of team activity.");
            col.Item().Text("Column chart - completed tasks").Bold();
            col.Item().Image(columnPng, 500);
            col.Item().Text($"Completed: {string.Join(", ", completed)}");
            col.Item().Text("Line chart - support requests").Bold();
            col.Item().Image(linePng, 500);
            col.Item().Text($"Requests: {string.Join(", ", requests)}");
        });
        page.Footer().AlignCenter().Text("Charts: static SVG converted to PNG at 2x scale.").FontSize(9);
    })).PublishPdf(reportPath);

    Console.WriteLine($"Sample {sample}: {reportPath}");
    return 0;
}
catch (Exception error)
{
    Console.Error.WriteLine($"Report failed: {error.Message}");
    return 1;
}

static byte[] RenderPng(ChartBuilder chart, string name, string outputDirectory)
{
    string svgPath = Path.Combine(outputDirectory, name + ".svg");
    File.WriteAllText(svgPath, chart.RenderToSvg());

    using var renderer = new SKSvg();
    var picture = renderer.Load(svgPath)
        ?? throw new InvalidOperationException("SVG could not be loaded.");
    using var png = new MemoryStream();
    using var colorSpace = SKColorSpace.CreateSrgb();
    if (!picture.ToImage(png, SKColors.White, SKEncodedImageFormat.Png, 100,
            2f, 2f, SKColorType.Rgba8888, SKAlphaType.Premul, colorSpace))
        throw new InvalidOperationException("SVG could not be converted to PNG.");
    byte[] pngBytes = png.ToArray();
    if (pngBytes.Length == 0)
        throw new InvalidOperationException("SVG conversion produced no PNG data.");
    File.WriteAllBytes(Path.Combine(outputDirectory, name + ".png"), pngBytes);
    Console.WriteLine($"Converted {name}: 800 x 450 SVG to 1600 x 900 PNG");
    return pngBytes;
}
