// App.tsx
import React, { useState } from "react";
import "./App.css";

/* ---------------- CHAT MESSAGE TYPE ---------------- */
type ChatMessage = {
  role: "user" | "bot";
  text: string;
  fileUrl?: string | null;
};

type ChatResponse = {
  response: string;
  download_url?: string;
};

function App() {
  const [message, setMessage] = useState("");
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  // ---------------- SEND MESSAGE ----------------
  const sendMessage = async () => {
    if (!message.trim()) return;

    const userMsg: ChatMessage = { role: "user", text: message };
    setChat(prev => [...prev, userMsg]);
    setMessage("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
      });

      const data = (await res.json()) as ChatResponse;

      setChat(prev => [
        ...prev,
        {
          role: "bot",
          text: data.response,
          fileUrl: data.download_url || null
        }
      ]);
    } catch (err) {
      console.error(err);
      setChat(prev => [
        ...prev,
        { role: "bot", text: "Server error. Try again." }
      ]);
    }

    setLoading(false);
  };

  // ---------------- UPLOAD PDF ----------------
  const uploadPDF = async () => {
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);

    try {
      const res = await fetch("http://localhost:5000/upload", {
        method: "POST",
        body: formData
      });

      const data = await res.json();

      setChat(prev => [
        ...prev,
        {
          role: "bot",
          text: "✅ PDF processed successfully!"
        }
      ]);
    } catch (err) {
      console.error(err);
      setChat(prev => [
        ...prev,
        { role: "bot", text: "Upload failed." }
      ]);
    }

    setLoading(false);
  };

  return (
    <div className="container">
      <h2>Job Assistant Bot</h2>

      {/* ---------------- CHAT BOX ---------------- */}
      <div className="chatbox">
        {chat.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div>{msg.text}</div>

            {/* Show download button if available */}
            {msg.fileUrl && (
              <a
                href={msg.fileUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="download-btn"
              >
                📥 Download Excel
              </a>
            )}
          </div>
        ))}
        {loading && <div className="message bot">Typing...</div>}
      </div>

      {/* ---------------- MESSAGE INPUT ---------------- */}
      <div className="input-area">
        <input
          value={message}
          placeholder="Type your message..."
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button onClick={sendMessage}>Send</button>
      </div>

      {/* ---------------- PDF UPLOAD ---------------- */}
      <div className="upload-area">
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
        />
        <button onClick={uploadPDF}>Upload PDF</button>
      </div>
    </div>
  );
}

export default App;