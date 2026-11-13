import { existsSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function withExtension(file) {
  for (const candidate of [file, `${file}.ts`, `${file}.tsx`, path.join(file, "index.ts")]) {
    if (existsSync(candidate) && !candidate.endsWith(path.sep)) return candidate;
  }
  return null;
}

export async function resolve(specifier, context, next) {
  let target = null;
  if (specifier.startsWith("@/")) {
    target = withExtension(path.join(ROOT, specifier.slice(2)));
  } else if (specifier.startsWith(".") && context.parentURL?.startsWith("file:")) {
    const base = path.dirname(fileURLToPath(context.parentURL));
    const file = path.resolve(base, specifier);
    if (!existsSync(file) || !path.extname(file)) target = withExtension(file);
  }
  return target ? next(pathToFileURL(target).href, context) : next(specifier, context);
}
