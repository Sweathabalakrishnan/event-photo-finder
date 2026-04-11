// import express from "express";
// import cors from "cors";
// import path from "path";
// import { ROOT } from "./utils/paths.js";
// import eventRoutes from "./routes/events.js";

// const app = express();

// app.use(cors());
// app.use(express.json());
// app.use("/api/events", eventRoutes);
// app.use("/uploads", express.static(path.join(ROOT, "uploads")));

// const PORT = 5000;
// app.listen(PORT, () => {
//   console.log(`Server running on http://localhost:${PORT}`);
// });

import express from "express";
import cors from "cors";
import path from "path";
import { ROOT } from "./utils/paths.js";
import eventRoutes from "./routes/events.js";

const app = express();

app.use(express.json());

app.use(
  cors({
    origin: [
      "http://localhost:5173",
      "https://event-photo-finder-sweatha.vercel.app"
    ],
    methods: ["GET", "POST", "PUT", "DELETE"],
    credentials: true
  })
);

app.get("/", (req, res) => {
  res.json({ status: "ok" });
});

app.use("/api/events", eventRoutes);
app.use("/uploads", express.static(path.join(ROOT, "uploads")));

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
