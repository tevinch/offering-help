import angular from "@angular-eslint/template-parser";
import betterTailwindcss from "eslint-plugin-better-tailwindcss";

export default [{
  files: ["**/*.html"],
  languageOptions: { parser: angular },
  plugins: { "better-tailwindcss": betterTailwindcss },
  settings: { "better-tailwindcss": { entryPoint: "styles.css" } },
  rules: {
    "better-tailwindcss/enforce-consistent-line-wrapping": ["error", {
      printWidth: 80, group: "newLine", preferSingleLine: false,
    }],
    "better-tailwindcss/enforce-consistent-class-order": "error",
  },
}];
