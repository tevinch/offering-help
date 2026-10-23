# Needle title regex and join

**RegEx join** supplies the separator between the items returned by a title's regular expression. If the expression returns just one item, changing join has no visible effect.

## A setting where join is visible

In an existing channel where you can configure Needle:

1. Run `/auto-thread` and choose **title-format: Custom**. Keep the other options as they are; note your existing title settings if you want to restore them.
2. Enter `/[a-z]+/g` in **Title format**.
3. Set **Max title length** to `100` while comparing these examples.
4. Enter a pipe surrounded by spaces in **RegEx join**: ` | `. Do not include quotes or backticks. Save the form.
5. Try a new message containing `red blue green` in that channel. The expected title is `red | blue | green`.

Changing join to `-` makes the same matches produce `red-blue-green`. Join does not add a prefix or suffix, and it does not split the message into words itself: the regex chooses the items first.

## Why the `g` flag matters

For the message `red blue green gold`, these title settings produce:

| Title format | Items returned by matching | Join | Expected title |
|---|---|---|---|
| `/[a-z]+/g` | `red`, `blue`, `green`, `gold` | `-` | `red-blue-green-gold` |
| `/[a-z]+/` | `red` | `-` | `red` |
| `/([a-z]+) ([a-z]+)/` | `red blue`, `red`, `blue` | `-` | `red blue-red-blue` |
| `/([a-z]+) ([a-z]+)/g` | `red blue`, `green gold` | `-` | `red blue-green gold` |

With `g`, JavaScript returns all full matches. Without `g`, it returns the first full match followed by its capturing groups. Capturing parentheses can therefore repeat part of the matched text in a title. Join is a separator, not a replacement template such as `$1`.

## Embed titles and line breaks

Needle passes the pattern and flags to JavaScript's `RegExp` constructor. The `m` flag is passed through; it makes `^` and `$` match line boundaries. Fixed text can surround the one slash-delimited expression, such as `Discuss /.../`. Runtime support and Needle's separate expression validation still apply.

The regex sees the cleaned message body, **two newlines**, then each embed's text in order:

```text
message body\n\n
first embed title\n\n
first embed description\n\n
field name\nfield value\n\n  (repeated for each field)
footer text\n\n
next embed title...          (repeated for each embed)
```

Here `\n` means a line-feed character; the display lines above are just labels. Missing title, description or footer text is empty, but its separators remain. Embed mentions are cleaned and message variables are removed before matching. The embed title is therefore not always the second line of the regex input.

For a one-line body `New report` and first embed title `Weekly summary`, the input begins `New report\n\nWeekly summary\n\n...`. The format `Discuss /(?<=\n).*?$/m` can match the **empty line** between the first two newlines. Its final title is just `Discuss `, including the trailing space.

If the cleaned message body has **no line breaks** (including an empty body), and the **first embed** title remains nonempty and single-line after mention cleaning and variable removal, this format selects that title:

```text
Discuss /(?<=^[^\r\n]*\n\n)[^\r\n]+/
```

Keep it without `m` or `g`: `^` must mean the beginning of the whole input. For the example above, the final title is `Discuss Weekly summary`. There is one full match and no capturing groups, so join has no visible effect.

This condition matters. A body `First\n\nSecond` makes the same expression select `Second`, because a blank paragraph can look identical to the separator before an embed. Without knowing the body format, this is not a general embed-title selector. A missing first embed title leaves the fixed prefix `Discuss `; a later embed's title is not substituted. Check the actual cleaned body and first embed title before using this setting.

The last three executable examples below show the blank-match case, the bounded selection, and that multiline counterexample. They use explicit synthetic input strings; they do not fetch or assemble Discord messages.

## Run the small examples locally

With Node.js available, download this directory and run:

```sh
node preview.mjs
node --test preview.test.mjs
```

There are no dependencies to install. Edit the `examples` array in [preview.mjs](preview.mjs) to change its synthetic messages, expressions and separators. Each output line is JSON containing the actual `matches` array and the `joined` text. For the first example:

```json
{"message":"red blue green","titleFormat":"/[a-z]+/g","join":" | ","matches":["red","blue","green"],"joined":"red | blue | green"}
```

This executable demonstrates JavaScript matching and joining on plain text, including synthetic strings that show the embed separators above. It does not connect to Discord or reproduce Needle's configuration validation, mention cleaning, embed assembly, variable expansion or title shortening.

## Other things that affect the final title

- **No match:** `/[0-9]+/g` on `red blue` gives no joined text. When the whole title format is just that expression, Needle falls back to `New Thread`. A fixed prefix can remain: `Topic: /[0-9]+/g` produces `Topic: `.
- **Length:** Needle shortens long titles with three dots. For example, `/[a-z]+/g`, join ` | ` and maximum `10` produce `red | b...` from `red blue green`. Use `100` when checking whether join is working.
- **Newlines:** Needle turns newlines in the assembled title into spaces. Its regex input can also include embed text and additional newlines, so a plain-message preview is not a full preview of those cases.
- **Pattern validity:** invalid regex syntax or flags are errors. Needle's configuration also checks unsafe expressions and permits only one slash-delimited regex in the title format. The local example does not replace those checks.
- **Variables:** fixed text and [Needle message variables](https://github.com/MarcusOtter/discord-needle/wiki/FAQ#message-variables) can surround the regex. The local example does not expand variables.

The final-title examples were checked offline by running the relevant methods from Needle's [released v3.5.0 source](https://github.com/MarcusOtter/discord-needle/blob/v3.5.0/src/services/ThreadCreationService.ts) and [current source checked October 21, 2026](https://github.com/MarcusOtter/discord-needle/blob/aefcd126abd8861d44d4afd53608b0fdeb093639/src/services/ThreadCreationService.ts). The original runnable example was checked with Node.js 24.19.0. The embed cases added October 23, 2026 were checked with Node.js 18.20.4: nine synthetic message structures were also run through the actual current title methods, with discord.js 14.25.1 mention cleaning and safe-regex 2.1.1 validation. These checks did not create Discord threads or verify the hosted instance's version, your settings or permissions.

References: JavaScript [`String.match`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/match), [`Array.join`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/join), Needle's [custom title form](https://github.com/MarcusOtter/discord-needle/blob/v3.5.0/src/modals/custom-title-format.ts) and [configuration command](https://github.com/MarcusOtter/discord-needle/blob/v3.5.0/src/commands/auto-thread.ts). This directory contains an original example using JavaScript built-ins; it does not include Needle's source code.

## Optional coffee

If this helped, you can buy me a coffee. It is entirely optional; the guide and examples are free.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
