import React, { useState, useEffect } from "react";
import { Mic, Send, LogOut } from "lucide-react";
import "./App.css";

import EmotionTimeline from "./components/EmotionTimeline";
import ReportDownload from "./components/ReportDownload";

/* -------------------- EMOTION COLORS -------------------- */
const EMOTION_COLORS = {
  joy: "#FFD166",
  amusement: "#FFC857",
  excitement: "#FF9F1C",
  gratitude: "#6BCF63",
  love: "#F77F9A",
  admiration: "#4ECDC4",
  pride: "#5BC0EB",
  optimism: "#A7E163",
  relief: "#9AE6B4",

  anger: "#D62828",
  annoyance: "#E76F51",
  disgust: "#6A994E",
  fear: "#5A189A",
  nervousness: "#7B2CBF",

  sadness: "#457B9D",
  grief: "#2C3E50",
  disappointment: "#6C757D",
  remorse: "#5F6CAF",
  embarrassment: "#B56576",

  confusion: "#8D99AE",
  curiosity: "#48CAE4",
  realization: "#4D96FF",
  surprise: "#56CFE1",
  neutral: "#ADB5BD",

  caring: "#52B788",
  approval: "#74C69D",
  disapproval: "#8B0000",
  desire: "#FF758F",
};

const getColor = (emotion) => EMOTION_COLORS[emotion] || "#9E9E9E";

/* ======================================================= */

function App() {
  /* ---------- AUTH STATE ---------- */
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [displayName, setDisplayName] = useState("");

  const [authMode, setAuthMode] = useState("login");
  const [identifier, setIdentifier] = useState(""); // username OR email
  const [email, setEmail] = useState(""); // signup only
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");

  /* ---------- APP STATE ---------- */
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);

  /* ======================================================= */

  useEffect(() => {
    if (token) fetchTimeline();
  }, [token]);

  /* -------------------- AUTH -------------------- */

  const logout = () => {
    localStorage.clear();
    setToken(null);
    setDisplayName("");
    setHistory([]);
    setResult(null);
  };

  const login = async () => {
    const formData = new URLSearchParams();
    formData.append("username", identifier);
    formData.append("password", password);

    const res = await fetch("http://localhost:8000/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Login failed");

    localStorage.setItem("token", data.access_token);
    setToken(data.access_token);
    setDisplayName(identifier);
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthError("");

    try {
      if (authMode === "signup") {
        const res = await fetch("http://localhost:8000/signup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: identifier,
            email: email,
            password: password,
          }),
        });

        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || "Signup failed");
        }
      }

      await login();
    } catch (err) {
      setAuthError(err.message);
    }
  };

  /* -------------------- TIMELINE -------------------- */

  const fetchTimeline = async () => {
    try {
      const res = await fetch("http://localhost:8000/timeline", {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401) {
        logout();
        return;
      }

      const data = await res.json();
      setHistory(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Timeline fetch error:", err);
      setHistory([]);
    }
  };

  /* -------------------- ANALYSIS -------------------- */

  const handleAnalyze = async (audioBlob = null) => {
    setLoading(true);
    const formData = new FormData();
    formData.append("date", new Date().toISOString().split("T")[0]);

    let url = "http://localhost:8000/analyze-text";

    if (audioBlob) {
      formData.append("file", audioBlob, "voice.webm");
      url = "http://localhost:8000/analyze-audio";
    } else {
      formData.append("text", text);
    }

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (res.status === 401) {
        logout();
        return;
      }

      const data = await res.json();
      setResult(data);
      setText("");
      fetchTimeline();
    } catch (err) {
      console.error("Analysis failed:", err);
    } finally {
      setLoading(false);
    }
  };

  /* -------------------- AUDIO -------------------- */

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    const chunks = [];

    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: "audio/webm" });
      stream.getTracks().forEach((t) => t.stop());
      handleAnalyze(blob);
    };

    recorder.start();
    setMediaRecorder(recorder);
    setIsRecording(true);
  };

  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  /* ===================== AUTH UI ===================== */

  if (!token) {
    return (
      <div className="app-container auth-container">
        <div className="card auth-card">
          <div className="logo-header">🧠</div>
          <h1>MindJournal</h1>
          <p>
            {authMode === "login"
              ? "Login with Username or Email"
              : "Create Account"}
          </p>

          <form onSubmit={handleAuth}>
            <input
              type="text"
              placeholder="Username"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
            />

            {authMode === "signup" && (
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            )}

            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            <button type="submit" className="primary-btn full-width">
              {authMode === "login" ? "Log In" : "Sign Up"}
            </button>
          </form>

          {authError && <div className="error-msg">{authError}</div>}

          <p
            className="toggle-text"
            onClick={() =>
              setAuthMode(authMode === "login" ? "signup" : "login")
            }
          >
            {authMode === "login"
              ? "New here? Create Account"
              : "Have an account? Log In"}
          </p>
        </div>
      </div>
    );
  }

  /* ===================== MAIN UI ===================== */

  return (
    <div className="app-container">
      <div className="main-card">
        <header className="app-header">
          <div>
            <h1>🧠 MindJournal</h1>
            <p className="user-badge">Logged in as {displayName}</p>
          </div>
          <button onClick={logout} className="icon-btn logout-btn">
            <LogOut size={18} /> Logout
          </button>
        </header>

        {/* INPUT SECTION */}
        <div className="input-section">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="How was your day? Type or record..."
          />

          <div className="controls">
            <button
              className={`icon-btn ${isRecording ? "recording" : ""}`}
              onClick={isRecording ? stopRecording : startRecording}
            >
              <Mic /> {isRecording ? "Stop" : "Record"}
            </button>

            <button
              className="primary-btn"
              onClick={() => handleAnalyze()}
              disabled={loading || (!text && !isRecording)}
            >
              {loading ? "Analyzing..." : "Analyze"} <Send size={16} />
            </button>
          </div>
        </div>

        {/* RESULT */}
        {result?.emotions && (
          <div
            className="result-section"
            style={{
              borderLeft: `6px solid ${
                result.emotions[0]
                  ? getColor(result.emotions[0])
                  : "#9E9E9E"
              }`,
            }}
          >
            <h2>
              {result.emotions.map((emo, idx) => (
                <span
                  key={emo}
                  style={{
                    color: getColor(emo),
                    marginRight: "6px",
                    textTransform: "uppercase",
                  }}
                >
                  {emo}
                  {idx < result.emotions.length - 1 ? "," : ""}
                </span>
              ))}
            </h2>

            {result.suggestion && (
              <div className="suggestion-box">
                <strong>Suggested Action</strong>
                <p>{result.suggestion}</p>
              </div>
            )}
          </div>
        )}

        {/* TIMELINE + REPORT */}
        <div className="history-section">
          <div className="history-header">
            <h3>📊 Emotional Journey</h3>
            <ReportDownload token={token} />
          </div>

          <p className="legend-hint">
            Timeline shows when emotions occurred over time
          </p>

          <div className="chart-container">
            <EmotionTimeline history={history} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
