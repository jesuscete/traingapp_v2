// Ejecuta tests TS sin dependencias: Node >= 23 quita los tipos; este hook resuelve "@/" y la extensión .ts.
import { register } from "node:module";

register("./test-loader.mjs", import.meta.url);
