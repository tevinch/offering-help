using System.Text.Json;
using Jint;

if (args is ["--check"])
{
    Acceptance.Run();
    return;
}

var engine = new Engine();
var host = new TemplateHost(engine);
var path = Path.Combine(AppContext.BaseDirectory, "templates", "hello.txt");
var rendered = engine.Evaluate($$"""
    (() => {
        const ctx = { a: 'wor', b: 'ld' };
        return template({{JsonSerializer.Serialize(path)}}, ctx);
    })()
    """).AsString();
Console.WriteLine(rendered);
