import { defineConfig } from "eslint/config";
import js from "@eslint/js";
import globals from "globals";
import prettier from "eslint-plugin-prettier";

export default defineConfig([
  {
    languageOptions: {
      globals: {
        ...globals.browser,
        Alpine: "readonly",
        __dirname: "readonly",
      },
    },
    files: ["**/*.js"],
    plugins: {
      js,
      prettier,
    },
    extends: ["js/recommended"],
    rules: {
      "no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          destructuredArrayIgnorePattern: "^_",
        },
      ],
      "no-undef": "warn",
      "prettier/prettier": "error",
    },
  },
]);
