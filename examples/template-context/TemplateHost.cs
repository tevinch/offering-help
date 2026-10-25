using System.Text;
using Jint;
using Jint.Native;
using Jint.Runtime.Interop;

internal sealed class TemplateHost
{
    public Engine Engine { get; }
    public int CallbackCount { get; private set; }
    public int FileReadCount { get; private set; }
    public int ExpressionCount { get; private set; }
    public List<string> ReadPaths { get; } = [];

    public TemplateHost(Engine engine)
    {
        Engine = engine;
        engine.SetValue("template", new ClrFunction(engine, "template", (_, args) =>
        {
            CallbackCount++;
            if (args.Length != 2 || !args[0].IsString())
                throw new ArgumentException("Use template(path, ctx) with a string path.");
            return RenderFile(args[0].AsString(), args[1]);
        }, 2));
    }

    private string RenderFile(string path, JsValue ctx)
    {
        var text = File.ReadAllText(path, Encoding.UTF8);
        FileReadCount++;
        ReadPaths.Add(path);
        var result = new StringBuilder();
        var position = 0;
        while (true)
        {
            var start = text.IndexOf("{{", position, StringComparison.Ordinal);
            if (start < 0)
            {
                result.Append(text, position, text.Length - position);
                return result.ToString();
            }
            result.Append(text, position, start - position);
            var end = text.IndexOf("}}", start + 2, StringComparison.Ordinal);
            if (end < 0) throw new FormatException("Missing closing }} delimiter.");
            var expression = text[(start + 2)..end];
            ExpressionCount++;
            var function = Engine.Evaluate("(function(ctx) { return (\n" + expression + "\n); })");
            // The received JsValue stays native and belongs to this same Engine.
            result.Append(Engine.Invoke(function, ctx).ToString());
            position = end + 2;
        }
    }
}
