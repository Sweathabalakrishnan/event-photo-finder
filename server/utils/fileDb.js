import fs from "fs";

export function readJson(path, fallback = []) {
  try {
    if (!fs.existsSync(path)) return fallback;
    const raw = fs.readFileSync(path, "utf-8");
    return JSON.parse(raw || "[]");
  } catch {
    return fallback;
  }
}

export function writeJson(path, data) {
  fs.writeFileSync(path, JSON.stringify(data, null, 2), "utf-8");
}