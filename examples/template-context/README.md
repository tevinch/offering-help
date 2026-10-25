# Pass a local JavaScript context through a C# template callback

A JavaScript caller can pass its local `ctx` object to a C# `ClrFunction`. To evaluate template expressions against that object, compile an anonymous function with a `ctx` parameter and invoke the function value with the received `JsValue`:

```csharp
var function = engine.Evaluate("(function(ctx) { return (\n" + expression + "\n); })");
var value = engine.Invoke(function, ctx);
```

`Engine.Evaluate(expression)` does not inherit the JavaScript caller's local bindings. Here, `ctx` is a function parameter. The native object remains in the same engine; no global `ctx` assignment, serialization or CLR object conversion is needed. Other caller locals are not captured. The built-in JavaScript `eval` is left intact.

The complete example registers `template(path, ctx)` in [TemplateHost.cs](TemplateHost.cs). Its C# callback reads a UTF8 file, evaluates each expression through the function above, and returns the full rendered string to JavaScript. [Program.cs](Program.cs) supplies a local context:

```javascript
(() => {
    const ctx = { a: 'wor', b: 'ld' };
    return template(path, ctx);
})()
```

With `hello, {{ ctx.a + ctx.b }}!` in the file, the result is `hello, world!`.

## Run

Use a .NET 8 SDK. Jint is pinned to **4.17.0** and the dependency lock file is included. From this directory:

```sh
dotnet restore --locked-mode
dotnet build --no-restore
dotnet run --no-build
dotnet run --no-build -- --check
```

The normal run prints `hello, world!`. The check run ends with `PASS: 22 native checks; full file rendering, counts, identity, globals and recovery.` It exercises actual files and the JavaScript → C# callback → JavaScript expression → rendered string path.

## Scope

The small scanner preserves literal text and treats the first `}}` after each `{{` as the end of an expression. An opening delimiter without a closing delimiter raises `FormatException`; a closing delimiter in literal text is preserved. It is not a JavaScript-aware parser: do not put the closing delimiter inside expression strings, comments or nested syntax. Empty and literal-only files work; this example does not provide delimiter escaping.

Use only templates and expressions you trust: expressions execute JavaScript in the existing engine. Keep the received `JsValue` in that same engine and render sequentially. This example does not capture caller locals or provide asynchronous rendering or concurrent engine access.

Checks were run natively on **macOS Arm64**, **.NET SDK 8.0.426 / runtime 8.0.32**, and **Jint 4.17.0**. They verify repeated and nested explicit contexts, native identity/prototypes/getters/methods/closures, unchanged global own keys and an existing global `ctx` sentinel, exact callback/file/expression counts, unchanged input files, and valid rendering after expression errors. Broken versions with missing callback registration, raw expression evaluation, global context assignment, an omitted expression invocation and a canned output were rejected. This verifies the supplied example; it does not establish behavior in another application's private template engine.

References: [Jint 4.17.0](https://github.com/sebastienros/jint/releases/tag/v4.17.0), [public Engine.Invoke overload](https://github.com/sebastienros/jint/blob/v4.17.0/Jint/Engine.cs), [native JsValue conversion](https://github.com/sebastienros/jint/blob/v4.17.0/Jint/Native/JsValue.cs).

## Optional coffee

This example is free. If it saves you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
