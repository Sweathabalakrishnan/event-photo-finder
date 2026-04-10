





import express from "express";
import multer from "multer";
import fs from "fs";
import path from "path";
import axios from "axios";
import FormData from "form-data";
import { nanoid } from "nanoid";
import { readJson, writeJson } from "../utils/fileDb.js";
import { EVENTS_DB, EVENTS_DIR, SELFIES_DIR } from "../utils/paths.js";

const router = express.Router();
const AI_BASE = "http://127.0.0.1:8000";

/* ---------------------------
   Multer setup for reference photos
---------------------------- */
const selfieStorage = multer.diskStorage({
  destination: function (req, file, cb) {
    cb(null, SELFIES_DIR);
  },
  filename: function (req, file, cb) {
    cb(null, `${Date.now()}-${file.originalname}`);
  }
});

const uploadSelfies = multer({ storage: selfieStorage });

/* ---------------------------
   Dynamic storage for event photos
---------------------------- */
function eventPhotoStorage(eventCode) {
  const dir = path.join(EVENTS_DIR, eventCode);

  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  return multer.diskStorage({
    destination: function (req, file, cb) {
      cb(null, dir);
    },
    filename: function (req, file, cb) {
      cb(null, `${Date.now()}-${file.originalname}`);
    }
  });
}

/* ---------------------------
   Create event
---------------------------- */
router.post("/", (req, res) => {
  try {
    const { name, date, venue } = req.body;

    if (!name || !date || !venue) {
      return res.status(400).json({
        error: "name, date, venue are required"
      });
    }

    const events = readJson(EVENTS_DB, []);
    const eventCode = nanoid(8);

    const event = {
      id: nanoid(12),
      eventCode,
      name,
      date,
      venue,
      createdAt: new Date().toISOString()
    };

    events.push(event);
    writeJson(EVENTS_DB, events);

    return res.json(event);
  } catch (error) {
    return res.status(500).json({
      error: "Failed to create event",
      details: error.message
    });
  }
});

/* ---------------------------
   Get event by code
---------------------------- */
router.get("/:eventCode", (req, res) => {
  try {
    const events = readJson(EVENTS_DB, []);
    const event = events.find((e) => e.eventCode === req.params.eventCode);

    if (!event) {
      return res.status(404).json({
        error: "Event not found"
      });
    }

    return res.json(event);
  } catch (error) {
    return res.status(500).json({
      error: "Failed to fetch event",
      details: error.message
    });
  }
});

/* ---------------------------
   Upload and index event photos
---------------------------- */
router.post(
  "/:eventCode/photos",
  (req, res, next) => {
    const storage = eventPhotoStorage(req.params.eventCode);
    const upload = multer({ storage }).array("photos", 100);
    upload(req, res, next);
  },
  async (req, res) => {
    try {
      const { eventCode } = req.params;

      if (!req.files || req.files.length === 0) {
        return res.status(400).json({
          error: "No photos uploaded"
        });
      }

      const indexed = [];
      const failed = [];

      for (const file of req.files) {
        try {
          const form = new FormData();
          form.append("event_code", eventCode);
          form.append("photo_path", file.path);

          const response = await axios.post(`${AI_BASE}/index-photo`, form, {
            headers: form.getHeaders(),
            maxBodyLength: Infinity,
            timeout: 120000
          });

          indexed.push({
            filename: path.basename(file.path),
            result: response.data
          });
        } catch (err) {
          failed.push({
            filename: path.basename(file.path),
            error:
              err?.response?.data?.error ||
              err?.response?.data?.details ||
              err.message
          });
        }
      }

      return res.json({
        message: "Photo indexing completed",
        totalUploaded: req.files.length,
        successCount: indexed.length,
        failedCount: failed.length,
        indexed,
        failed
      });
    } catch (error) {
      return res.status(500).json({
        error: "Indexing failed",
        details: error.message
      });
    }
  }
);

/* ---------------------------
   Match multiple reference photos
---------------------------- */
router.post(
  "/:eventCode/match",
  uploadSelfies.array("selfies", 3),
  async (req, res) => {
    try {
      const { eventCode } = req.params;

      if (!req.files || req.files.length < 2) {
        return res.status(400).json({
          error: "At least 2 reference photos are required"
        });
      }

      const form = new FormData();
      form.append("event_code", eventCode);

      req.files.forEach((file) => {
        form.append("selfie_paths", file.path);
      });

      const response = await axios.post(`${AI_BASE}/match-selfie`, form, {
        headers: form.getHeaders(),
        maxBodyLength: Infinity,
        timeout: 120000
      });

      const matches = (response.data.matches || []).map((filename) => ({
        filename,
        imageUrl: `http://localhost:5000/uploads/events/${eventCode}/${encodeURIComponent(
          filename
        )}`
      }));

      return res.json({
        message: "Matching completed",
        matches,
        count: matches.length
      });
    } catch (error) {
      return res.status(500).json({
        error: "Matching failed",
        details:
          error?.response?.data?.error ||
          error?.response?.data?.details ||
          error.message
      });
    }
  }
);

export default router;
