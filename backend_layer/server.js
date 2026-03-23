// server.js
import express from "express";
import multer from "multer";
import axios from "axios";
import fs from "fs";
import FormData from "form-data";
import cors from "cors";

const app = express();
const PORT = 5000;

// Configure multer for file uploads
const upload = multer({ dest: "uploads/" });

// Middleware
app.use(cors());

app.use(express.json());

/* ---------------- HEALTH CHECK ---------------- */
app.get("/health", (req, res) => {
  res.json({ status: "Node.js server running" });
});

/* ---------------- CHAT ENDPOINT (NEW) ---------------- */
app.post("/chat", async (req, res) => {
  try {
    const { message } = req.body;

    const response = await axios.post(
      "http://localhost:8000/chat",
      { message }
    );

    res.json({
      response:
        response.data.response ||
        response.data.answer ||
        response.data.message
    });

  } catch (error) {
    console.error("Chat Error:", error.message);

    res.status(500).json({
      response: "AI server error"
    });
  }
});
/* ---------------- UPLOAD ENDPOINT ---------------- */
app.post("/upload", upload.single("file"), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: "No file uploaded" });

  try {
    const form = new FormData();
    form.append("file", fs.createReadStream(req.file.path));

    const response = await axios.post(
      "http://localhost:8000/upload/",
      form,
      {
        headers: form.getHeaders(),
        maxContentLength: Infinity,
        maxBodyLength: Infinity,
      }
    );

    // Delete temp file
    fs.unlinkSync(req.file.path);

    res.json(response.data);

  } catch (err) {
    console.error("Error forwarding to FastAPI:", err.message);
    res.status(500).json({ error: err.message });
  }
});

/* ---------------- ROOT ---------------- */
app.get("/", (req, res) => {
  res.send("Server working");
});

/* ---------------- START SERVER ---------------- */
app.listen(PORT, () => {
  console.log(`Node.js server running on http://localhost:${PORT}`);
});