import React, { useState } from "react";
import "./App.css";

function App() {
  const [message, setMessage] = useState("");
  const [chat, setChat] = useState<any[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  // -------- CHAT ----------
  const sendMessage = async () => {
    if (!message.trim()) return;

    const userMsg = { role: "user", text: message };
    setChat(prev => [...prev, userMsg]);
    setMessage("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:5000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message })
      });

      const data = await res.json();

      setChat(prev => [
        ...prev,
        { role: "bot", text: data.response }
      ]);
    } catch {
      setChat(prev => [
        ...prev,
        { role: "bot", text: "Server error. Try again." }
      ]);
    }

    setLoading(false);
  };

  // -------- UPLOAD ----------
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
        { role: "bot", text: "✅ PDF processed successfully!" }
      ]);
    } catch {
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

      <div className="chatbox">
        {chat.map((msg, i) => (
          <div key={i} className={msg.role}>
            {msg.text}
          </div>
        ))}
        {loading && <div className="bot">Typing...</div>}
      </div>

      {/* MESSAGE INPUT */}
      <div className="input-area">
        <input
          value={message}
          placeholder="Type your message..."
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button onClick={sendMessage}>Send</button>
      </div>

      {/* OPTIONAL UPLOAD */}
      <div className="upload-area">
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) =>
            setFile(e.target.files ? e.target.files[0] : null)
          }
        />
        <button onClick={uploadPDF}>Upload PDF</button>
      </div>
    </div>
  );
}

export default App;