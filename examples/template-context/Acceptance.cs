using System.Text.Json;
using Jint;
using Jint.Runtime;

internal static class Acceptance
{
    private static int checks;

    public static void Run()
    {
        foreach (var sentinel in new[] { false, true })
        {
            var engine = new Engine();
            var builtInEval = engine.GetValue("eval");
            if (sentinel)
                engine.Evaluate("globalThis.ctx = { a: 'global', b: '-sentinel' }");
            var host = new TemplateHost(engine);
            Require(ReferenceEquals(engine.GetValue("eval"), builtInEval), "Registration replaced built-in eval");

            Check(host, "hello.txt", "const ctx = { a: 'wor', b: 'ld' }; return template(path, ctx);", "hello, world!", 1);
            Check(host, "multi.txt", "const ctx = { a: 'red', b: 'blue' }; return template(path, ctx);", "α red / blue / redblue ω", 3);
            Check(host, "hello.txt", "const ctx = { a: 'new', b: ' value' }; return template(path, ctx);", "hello, new value!", 1);
            Check(host, "hello.txt", """
                const ctx = { a: 'out', b: 'er' };
                const outer = ctx;
                return (() => {
                    const ctx = { a: 'in', b: 'ner' };
                    return template(path, ctx) + '|' + template(path, outer);
                })();
                """, "hello, inner!|hello, outer!", 2, 2);
            Check(host, "identity.txt", """
                let reads = 0;
                const prototype = { label: 'inherited' };
                const ctx = Object.create(prototype);
                ctx.a = 'wor'; ctx.b = 'ld';
                ctx.self = () => ctx;
                ctx.join = function () { return this.a + this.b; };
                Object.defineProperty(ctx, 'value', { get() { reads++; return 'getter'; }, enumerable: true });
                const keys = Reflect.ownKeys(ctx);
                const descriptor = Object.getOwnPropertyDescriptor(ctx, 'value');
                const rendered = template(path, ctx);
                if (reads !== 1 || Object.getPrototypeOf(ctx) !== prototype ||
                    JSON.stringify(Reflect.ownKeys(ctx)) !== JSON.stringify(keys) ||
                    Object.getOwnPropertyDescriptor(ctx, 'value').get !== descriptor.get ||
                    ctx.self() !== ctx || ctx.a !== 'wor' || ctx.b !== 'ld')
                    throw new Error('Native input changed');
                return rendered;
                """, "true|world|inherited|getter", 4);
            Check(host, "empty.txt", "return template(path, {});", "", 0);
            Check(host, "literal.txt", "return template(path, {});", "literal λ and }}", 0);
            CheckError<FormatException>(host, "unclosed.txt", 0);
            CheckError<JavaScriptException>(host, "missing.txt", 1);
            CheckError<JavaScriptException>(host, "syntax.txt", 1);
            Check(host, "hello.txt", "const ctx = { a: 'still ', b: 'works' }; return template(path, ctx);", "hello, still works!", 1);
        }
        Console.WriteLine($"PASS: {checks} native checks; full file rendering, counts, identity, globals and recovery.");
    }

    private static void Check(TemplateHost host, string name, string body, string expected, int expressions, int calls = 1)
    {
        var path = Path.Combine(AppContext.BaseDirectory, "templates", name);
        var original = File.ReadAllBytes(path);
        var before = Counts(host);
        var actual = host.Engine.Evaluate(Guarded(path, body)).AsString();
        Require(actual == expected, $"{name}: expected '{expected}', got '{actual}'");
        VerifyCounts(host, before, calls, expressions, path);
        Require(File.ReadAllBytes(path).SequenceEqual(original), $"{name}: file changed");
        checks++;
        Console.WriteLine($"PASS: {name}; callbacks={calls}, reads={calls}, expressions={expressions}; result={actual}");
    }

    private static void CheckError<T>(TemplateHost host, string name, int expressions) where T : Exception
    {
        var path = Path.Combine(AppContext.BaseDirectory, "templates", name);
        var original = File.ReadAllBytes(path);
        var before = Counts(host);
        var globalKeys = host.Engine.Evaluate("JSON.stringify(Reflect.ownKeys(globalThis))").AsString();
        var globalCtx = host.Engine.Evaluate("globalThis.ctx");
        var eval = host.Engine.Evaluate("globalThis.eval");
        var sentinelValue = host.Engine.Evaluate("JSON.stringify(globalThis.ctx)").ToString();
        Exception? failure = null;
        try { host.Engine.Evaluate(Guarded(path, "return template(path, {});")); }
        catch (Exception error) { failure = error; }
        Require(failure is T, $"{name}: expected {typeof(T).Name}, got {failure?.GetType().Name ?? "no error"}");
        VerifyCounts(host, before, 1, expressions, path);
        Require(host.Engine.Evaluate("JSON.stringify(Reflect.ownKeys(globalThis))").AsString() == globalKeys, "Error changed global keys");
        Require(ReferenceEquals(host.Engine.Evaluate("globalThis.ctx"), globalCtx), "Error changed global ctx identity");
        Require(ReferenceEquals(host.Engine.Evaluate("globalThis.eval"), eval), "Error replaced built-in eval");
        Require(host.Engine.Evaluate("JSON.stringify(globalThis.ctx)").ToString() == sentinelValue, "Error changed sentinel fields");
        Require(File.ReadAllBytes(path).SequenceEqual(original), "Error changed file bytes");
        checks++;
        Console.WriteLine($"PASS: {name} propagated {failure!.GetType().Name}; globals/file preserved");
    }

    private static string Guarded(string path, string body) => $$"""
        (() => {
            const path = {{JsonSerializer.Serialize(path)}};
            const keys = JSON.stringify(Reflect.ownKeys(globalThis));
            const hadCtx = Object.hasOwn(globalThis, 'ctx');
            const originalCtx = globalThis.ctx;
            const sentinelValue = JSON.stringify(originalCtx);
            const originalEval = globalThis.eval;
            const result = (() => { {{body}} })();
            if (JSON.stringify(Reflect.ownKeys(globalThis)) !== keys ||
                Object.hasOwn(globalThis, 'ctx') !== hadCtx ||
                globalThis.ctx !== originalCtx || JSON.stringify(globalThis.ctx) !== sentinelValue ||
                globalThis.eval !== originalEval ||
                (!hadCtx && typeof ctx !== 'undefined'))
                throw new Error('Global bindings changed');
            return result;
        })()
        """;

    private static (int Calls, int Reads, int Expressions) Counts(TemplateHost host) =>
        (host.CallbackCount, host.FileReadCount, host.ExpressionCount);

    private static void VerifyCounts(TemplateHost host, (int Calls, int Reads, int Expressions) before, int calls, int expressions, string path)
    {
        Require(host.CallbackCount - before.Calls == calls, "Callback count missing/wrong");
        Require(host.FileReadCount - before.Reads == calls, "Actual file read count missing/wrong");
        Require(host.ExpressionCount - before.Expressions == expressions, "Expression evaluation count missing/wrong");
        Require(host.ReadPaths.Skip(before.Reads).SequenceEqual(Enumerable.Repeat(path, calls)), "Wrong files read");
    }

    private static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }
}
