import path from "path";
import { fileURLToPath } from "url";
import fs from "fs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export const ROOT = path.join(__dirname, "..");
export const DATA_DIR = path.join(ROOT, "data");
export const UPLOADS_DIR = path.join(ROOT, "uploads");
export const EVENTS_DIR = path.join(UPLOADS_DIR, "events");
export const SELFIES_DIR = path.join(UPLOADS_DIR, "selfies");
export const EVENTS_DB = path.join(DATA_DIR, "events.json");

[DATA_DIR, UPLOADS_DIR, EVENTS_DIR, SELFIES_DIR].forEach((dir) => {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});