import { pathToFileURL } from "node:url";

// The join value separates returned matches, rather than words in the input.
export function inspectMatches(message, expression, separator) {
  const matches = message.match(expression);
  return {
    matches: matches === null ? null : Array.from(matches),
    joined: matches?.join(separator) ?? "",
  };
}

const examples = [
  { message: "red blue green", expression: /[a-z]+/g, join: " | " },
  { message: "red blue green", expression: /[a-z]+/, join: " | " },
  { message: "red blue green gold", expression: /([a-z]+) ([a-z]+)/, join: " | " },
  { message: "red blue green gold", expression: /([a-z]+) ([a-z]+)/g, join: " | " },
  { message: "red blue", expression: /[0-9]+/g, join: " | " },
  { message: "café 茶", expression: /[^\s]+/gu, join: " / " },
  // Synthetic, already assembled input: body, blank line, first embed title,
  // blank line, description, then the empty footer and trailing separator.
  { message: "New report\n\nWeekly summary\n\nDetails\n\n\n\n", expression: /(?<=\n).*?$/m, join: "" },
  { message: "New report\n\nWeekly summary\n\nDetails\n\n\n\n", expression: /(?<=^[^\r\n]*\n\n)[^\r\n]+/, join: "" },
  // Outside the no-line-breaks body condition: this selects body text, not a title.
  { message: "First\n\nSecond\n\nWeekly summary\n\nDetails\n\n\n\n", expression: /(?<=^[^\r\n]*\n\n)[^\r\n]+/, join: "" },
];

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  for (const example of examples) {
    console.log(JSON.stringify({
      message: example.message,
      titleFormat: example.expression.toString(),
      join: example.join,
      ...inspectMatches(example.message, example.expression, example.join),
    }));
  }
}
