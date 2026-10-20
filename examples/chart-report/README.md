# Chart report

Create a PDF report containing a column chart and a line chart from TerraFluent.Chart.Reporting. The example saves the original SVGs, converts them to PNG with Svg.Skia, and embeds the PNG bytes using TerraFluent.Pdf.Reporting.

The PDF image API accepts PNG and JPEG. `RenderToBytes()` returns SVG bytes, so passing that result directly to `Image()` does not convert the image.

## Run

Install the [.NET 10 SDK](https://dotnet.microsoft.com/en-us/download/dotnet/10.0). Download this directory, open a terminal here, and run:

```sh
dotnet restore --locked-mode
dotnet run --no-restore -- A "./output-a"
dotnet run --no-restore -- B "./output-b"
```

Each sample produces `column.svg`, `column.png`, `line.svg`, `line.png`, and `report.pdf`. Open the PDF to see both charts, their captions, and the input values. A and B use different synthetic task and support counts. Change the sample values in `Program.cs` to use your own data.

The output directory must be new or empty. A nonempty directory is rejected before any output is written. Use a different directory for each run, or remove an earlier generated directory yourself. Existing documents are never merged or overwritten. A failed run can leave partial generated files in its output directory.

The project pins Chart 2.1.0, PDF 2.2.1, and Svg.Skia 5.2.3. The lock file fixes their transitive dependencies. Svg.Skia adds managed and native Skia/HarfBuzz dependencies; the PDF package's own zero-dependency description does not apply to this complete example. Restore downloads these packages; report generation then runs locally.

## The conversion

The important steps are:

```csharp
string svg = ChartBuilder.Create()
    .Size(800, 450)
    .AsStatic()
    .Legend(legend => legend.AtBottom().Padding(6))
    // Set the chart title, axes and series here.
    .RenderToSvg();

File.WriteAllText(svgPath, svg);
using var renderer = new SKSvg();
var picture = renderer.Load(svgPath)
    ?? throw new InvalidOperationException("SVG could not be loaded.");
using var png = new MemoryStream();
using var colorSpace = SKColorSpace.CreateSrgb();
if (!picture.ToImage(png, SKColors.White, SKEncodedImageFormat.Png, 100,
        2f, 2f, SKColorType.Rgba8888, SKAlphaType.Premul, colorSpace))
    throw new InvalidOperationException("SVG could not be converted to PNG.");
byte[] pngBytes = png.ToArray();

// Inside the PDF content column:
col.Item().Image(pngBytes, 500);
```

See `Program.cs` for the complete chart definitions and `PdfDocument.Create(...).PublishPdf(...)` call. The fixed size and `AsStatic()` avoid responsive dimensions and animation in a document export. A compact bottom legend keeps these sample charts at 800 x 450; longer labels, titles or a different legend layout can increase the actual SVG height. When changing the chart, check its actual dimensions rather than assuming the requested size is always the final size.

The conversion produces 1600 x 900 PNGs. At a PDF width of 500 points, this is about 230 pixels per inch. Raise the scale for larger placement or high resolution printing, at the cost of memory and file size. The embedded charts are raster images: chart text is not selectable as PDF text, and individual chart elements cannot be edited in the PDF. The original SVG files remain available separately.

## Check the output

The optional checks need Python 3 with Pillow and pypdf (checked with Python 3.12, Pillow 12.3 and pypdf 6.10). Install them in a Python environment with `python -m pip install Pillow pypdf`, then run:

```sh
python verify.py "./output-a" A "./output-b"
```

The check reads the SVG dimensions, labels and static elements, decodes the PNGs, and requires both PNGs' decoded pixels to match images embedded in the one-page PDF. It also checks the report text and that A/B data changes affect the plotted image region. This script checks the supplied sample data; update its expected values if you change that data. Open the PDF as well to review its appearance.

## Checked scope

Checked on macOS 14.6 arm64 with .NET SDK 10.0.402 and runtime 10.0.13. Both synthetic samples produced one-page PDFs containing two 1600 x 900 embedded images with exact decoded-pixel matches to the generated PNGs. The PDF pages were also rendered with Poppler and inspected for readable axes, values and legends. This was scripted execution and software-rendered output inspection. It does not establish behavior in the original application, other chart types or other operating systems. Other systems can need their own native renderer dependencies. The example handles its own generated static SVGs, not arbitrary downloaded SVG content.

- [Chart static export guidance](https://github.com/sahebansari/TerraFluent.Chart.Reporting/blob/main/docs/advanced.md)
- [PDF image formats and byte input](https://github.com/sahebansari/TerraFluent.Pdf.Reporting/blob/main/docs/images.md)
- [Svg.Skia conversion examples](https://github.com/wieslawsoltes/Svg.Skia#usage)
- [Original integration question](https://github.com/sahebansari/TerraPDF/discussions/8)

## Optional coffee

This example is free. If it saved you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
