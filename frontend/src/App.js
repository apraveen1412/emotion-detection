import React, { useState, useEffect, useRef } from "react";
import { Mic, Send, LogOut, Calendar, Settings, X, CheckCircle } from "lucide-react";
import "./App.css";

import EmotionBarChart from "./components/EmotionBarChart";
import ReportDownload from "./components/ReportDownload";

const EMOTION_COLORS = {
  joy: "#FFD166", amusement: "#FFC857", excitement: "#FF9F1C", gratitude: "#6BCF63",
  love: "#F77F9A", admiration: "#4ECDC4", pride: "#5BC0EB", optimism: "#A7E163",
  relief: "#9AE6B4", anger: "#D62828", annoyance: "#E76F51", disgust: "#6A994E",
  fear: "#5A189A", nervousness: "#7B2CBF", sadness: "#457B9D", grief: "#2C3E50",
  disappointment: "#6C757D", remorse: "#5F6CAF", embarrassment: "#B56576",
  confusion: "#8D99AE", curiosity: "#48CAE4", realization: "#4D96FF",
  surprise: "#56CFE1", neutral: "#ADB5BD", caring: "#52B788", approval: "#74C69D",
  disapproval: "#8B0000", desire: "#FF758F",
};

const getColor = (emotion) => EMOTION_COLORS[emotion] || "#9E9E9E";

function App() {
  /* ---------- AUTH & PROFILE STATE ---------- */
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [displayName, setDisplayName] = useState("");
  const [authMode, setAuthMode] = useState("login");
  const [identifier, setIdentifier] = useState(""); 
  const [email, setEmail] = useState(""); 
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");

  const [showProfile, setShowProfile] = useState(false);
  const [morningTime, setMorningTime] = useState("06:00");
  const [eveningTime, setEveningTime] = useState("17:00");
  const [profileMsg, setProfileMsg] = useState("");

  /* ---------- APP STATE ---------- */
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);

  /* ---------- SCHEDULING STATE ---------- */
  const [scheduledTime, setScheduledTime] = useState("");
  const [scheduleStatus, setScheduleStatus] = useState("");
  const [isScheduled, setIsScheduled] = useState(false);
  
  const [countdown, setCountdown] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    if (token) {
      fetchTimeline();
      fetchProfile();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (countdown === null) return;
    
    if (countdown === 0) {
      handleSchedule("auto");
      setCountdown(null);
      return;
    }

    timerRef.current = setTimeout(() => {
      setCountdown((prev) => prev - 1);
    }, 1000);

    return () => clearTimeout(timerRef.current);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [countdown]);

  /* -------------------- PROFILE / SETTINGS -------------------- */
  const fetchProfile = async () => {
    try {
      const res = await fetch("http://localhost:8000/profile", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setMorningTime(data.default_morning_time);
        setEveningTime(data.default_evening_time);
      }
    } catch (err) { console.error(err); }
  };

  const saveProfile = async () => {
    try {
      setProfileMsg("Saving...");
      const res = await fetch("http://localhost:8000/profile", {
        method: "PUT",
        headers: { 
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}` 
        },
        body: JSON.stringify({
          default_morning_time: morningTime,
          default_evening_time: eveningTime
        })
      });
      if (res.ok) setProfileMsg("Preferences Saved!");
      else setProfileMsg("Failed to save.");
      
      setTimeout(() => setProfileMsg(""), 3000);
    } catch (err) { setProfileMsg("Error saving."); }
  };

  /* -------------------- AUTH -------------------- */
  const logout = () => {
    localStorage.clear();
    setToken(null);
    setDisplayName("");
    setHistory([]);
    setResult(null);
    setCountdown(null);
    setIsScheduled(false);
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
          body: JSON.stringify({ username: identifier, email: email, password: password }),
        });
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || "Signup failed");
        }
      }
      await login();
    } catch (err) { setAuthError(err.message); }
  };

  /* -------------------- TIMELINE -------------------- */
  const fetchTimeline = async () => {
    try {
      const res = await fetch("http://localhost:8000/timeline", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.status === 401) { logout(); return; }
      const data = await res.json();
      setHistory(Array.isArray(data) ? data : []);
    } catch (err) { console.error(err); }
  };

  /* -------------------- ANALYSIS -------------------- */
  const handleAnalyze = async (audioBlob = null) => {
    setLoading(true);
    setScheduleStatus(""); 
    setCountdown(null); 
    setIsScheduled(false); 

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
      if (res.status === 401) { logout(); return; }
      
      const data = await res.json();
      setResult(data);
      setText("");
      fetchTimeline();

      if (data.requires_scheduling) {
        setCountdown(30);
      }

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
    if (mediaRecorder) { mediaRecorder.stop(); setIsRecording(false); }
  };

  /* -------------------- SCHEDULING -------------------- */
  const handleSchedule = async (timeMode = null) => {
    if (timeMode !== "auto") setCountdown(null);

    const timeToSubmit = timeMode === "auto" ? "auto" : scheduledTime;
    if (!timeToSubmit || !result?.suggestion) return;
    
    try {
      setScheduleStatus("Scheduling...");
      
      const formattedSuggestion = `OBSERVATION:\n${result.suggestion.observation}\n\nINSIGHTS:\n${result.suggestion.insight}\n\nACTIONABLE STEP:\n${result.suggestion.action}`;

      const formData = new FormData();
      formData.append("suggestion", formattedSuggestion);
      formData.append("scheduled_time", timeToSubmit);

      const res = await fetch("http://localhost:8000/schedule-activity", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const data = await res.json();

      if (res.ok) {
        setScheduleStatus(`✅ ${data.message}`);
        setIsScheduled(true); 
      } else {
        setScheduleStatus("❌ Failed to schedule");
      }
    } catch (err) {
      console.error(err);
      setScheduleStatus("❌ Error connecting to server");
    }
  };

  /* ===================== AUTH UI ===================== */
  if (!token) {
    return (
      <div className="app-container auth-container">
        <div className="card auth-card">
          <div className="logo-header">🧠</div>
          <h1>MindJournal</h1>
          <p>{authMode === "login" ? "Login with Username or Email" : "Create Account"}</p>
          <form onSubmit={handleAuth}>
            <input type="text" placeholder="Username" value={identifier} onChange={(e) => setIdentifier(e.target.value)} required />
            {authMode === "signup" && <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />}
            <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            <button type="submit" className="primary-btn full-width">{authMode === "login" ? "Log In" : "Sign Up"}</button>
          </form>
          {authError && <div className="error-msg">{authError}</div>}
          <p className="toggle-text" onClick={() => setAuthMode(authMode === "login" ? "signup" : "login")}>
            {authMode === "login" ? "New here? Create Account" : "Have an account? Log In"}
          </p>
        </div>
      </div>
    );
  }

  /* ===================== MAIN UI ===================== */
  return (
    <div className="app-container">
      <div className="main-card" style={{ position: "relative" }}>
        
        {/* OVERLAY FOR PROFILE SETTINGS */}
        {showProfile && (
          <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(255,255,255,0.95)", zIndex: 50, borderRadius: "20px", padding: "40px", display: "flex", flexDirection: "column" }}>
             <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
                <h2 style={{ margin: 0 }}>⚙️ Profile & Scheduling Preferences</h2>
                <button onClick={() => setShowProfile(false)} className="icon-btn"><X size={18}/></button>
             </div>
             
             <div style={{ background: "#f9fafb", padding: "20px", borderRadius: "10px", marginBottom: "20px" }}>
               <p style={{ color: "#4b5563", marginBottom: "15px" }}>If you don't pick a specific time, MindJournal will automatically schedule activities for the closest upcoming default time.</p>
               
               <label style={{ display: "block", fontWeight: "bold", marginBottom: "8px" }}>Default Morning Schedule</label>
               <input type="time" value={morningTime} onChange={(e) => setMorningTime(e.target.value)} style={{ padding: "10px", borderRadius: "6px", border: "1px solid #d1d5db", marginBottom: "20px", width: "100%", boxSizing: "border-box" }}/>
               
               <label style={{ display: "block", fontWeight: "bold", marginBottom: "8px" }}>Default Evening Schedule</label>
               <input type="time" value={eveningTime} onChange={(e) => setEveningTime(e.target.value)} style={{ padding: "10px", borderRadius: "6px", border: "1px solid #d1d5db", marginBottom: "20px", width: "100%", boxSizing: "border-box" }}/>
               
               <button onClick={saveProfile} className="primary-btn">Save Preferences</button>
               {profileMsg && <span style={{ marginLeft: "15px", color: "#4f46e5", fontWeight: "bold" }}>{profileMsg}</span>}
             </div>
          </div>
        )}

        <header className="app-header">
          <div>
            <h1>MindJournal</h1>
            <p className="user-badge">Logged in as {displayName}</p>
          </div>
          <div style={{ display: "flex", gap: "10px" }}>
            <button onClick={() => setShowProfile(true)} className="icon-btn">
              <Settings size={18} /> Settings
            </button>
            <button onClick={logout} className="icon-btn logout-btn">
              <LogOut size={18} /> Logout
            </button>
          </div>
        </header>

        {/* INPUT SECTION */}
        <div className="input-section">
          <textarea
            value={text}
            placeholder="How was your day?"
            onChange={(e) => setText(e.target.value)}
            onInput={(e) => {
              e.target.style.height = "auto";
              e.target.style.height = e.target.scrollHeight + "px";
            }}
          />
          <div className="controls">
            <button className={`icon-btn ${isRecording ? "recording" : ""}`} onClick={isRecording ? stopRecording : startRecording}>
              <Mic /> {isRecording ? "Stop" : "Record"}
            </button>
            <button className="primary-btn" onClick={() => handleAnalyze()} disabled={loading || (!text && !isRecording)}>
              {loading ? "Analyzing..." : "Analyze"} <Send size={16} />
            </button>
          </div>
        </div>

        {/* RESULT */}
        {result?.emotions && (
          <div className="result-section" style={{ borderLeft: `6px solid ${result.emotions[0] ? getColor(result.emotions[0]) : "#9E9E9E"}` }}>
            
            {result.input_text && (
              <div style={{ marginBottom: "15px", fontSize: "1.05rem", color: "#374151", fontStyle: "italic", padding: "12px", background: "#f3f4f6", borderRadius: "8px" }}>
                "{result.input_text}"
              </div>
            )}

            <h2>
              {result.emotions.map((emo, idx) => (
                <span key={emo} style={{ color: getColor(emo), marginRight: "6px", textTransform: "uppercase" }}>
                  {emo}{idx < result.emotions.length - 1 ? "," : ""}
                </span>
              ))}
            </h2>

            {result.suggestion && result.suggestion.observation && (
              <div className="suggestion-box" style={{ background: "#ffffff", border: "1px solid #e5e7eb", borderRadius: "12px", padding: "20px", marginTop: "20px", boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05)" }}>
                <h3 style={{ marginTop: 0, color: "#111827", borderBottom: "1px solid #e5e7eb", paddingBottom: "10px", fontSize: "1.1rem" }}>📋 Emotional Insights</h3>
                
                <div style={{ marginBottom: "16px", marginTop: "16px" }}>
                  <strong style={{ color: "#4f46e5", display: "block", marginBottom: "4px", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Observation</strong>
                  <p style={{ margin: 0, color: "#374151", lineHeight: "1.5" }}>{result.suggestion.observation}</p>
                </div>

                <div style={{ marginBottom: "16px" }}>
                  <strong style={{ color: "#4f46e5", display: "block", marginBottom: "4px", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Insight</strong>
                  <p style={{ margin: 0, color: "#374151", lineHeight: "1.5" }}>{result.suggestion.insight}</p>
                </div>

                <div style={{ marginBottom: "16px" }}>
                  <strong style={{ color: "#4f46e5", display: "block", marginBottom: "4px", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Actionable Step</strong>
                  <p style={{ margin: 0, color: "#374151", lineHeight: "1.5" }}>{result.suggestion.action}</p>
                </div>

                {/* ONLY SHOW SCHEDULING UI IF NEGATIVE EMOTIONS EXIST AND IT IS NOT YET SCHEDULED */}
                {result.requires_scheduling && !isScheduled && (
                  <div style={{ marginTop: "20px", borderTop: "1px solid #e5e7eb", paddingTop: "15px" }}>
                    {countdown !== null && (
                      <div style={{ background: "#fef3c7", border: "1px solid #fde68a", color: "#d97706", padding: "10px", borderRadius: "8px", fontWeight: "600", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <span>⏱️ Auto-scheduling closest default time in {countdown}s...</span>
                        <button onClick={() => setCountdown(null)} style={{ background: "transparent", border: "none", color: "#92400e", cursor: "pointer", fontWeight: "bold" }}>Cancel</button>
                      </div>
                    )}

                    <div style={{ marginTop: "10px", padding: "12px", background: "#f9fafb", borderRadius: "8px", display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
                        <Calendar size={18} color="#6b7280" />
                        <input 
                          type="datetime-local" 
                          value={scheduledTime} 
                          onChange={(e) => {
                            setScheduledTime(e.target.value);
                            setCountdown(null); 
                          }} 
                          style={{ padding: "8px", borderRadius: "6px", border: "1px solid #d1d5db", outline: "none", fontFamily: "inherit" }}
                        />
                        <button 
                          onClick={() => handleSchedule()} 
                          disabled={!scheduledTime || scheduleStatus.includes("Scheduling")}
                          className="primary-btn" 
                          style={{ padding: "8px 16px", fontSize: "0.9rem" }}>
                          Pick Custom Time
                        </button>
                        {scheduleStatus && !scheduleStatus.includes("✅") && (
                          <span style={{ fontSize: "0.85rem", color: "#ef4444", fontWeight: "600" }}>
                            {scheduleStatus}
                          </span>
                        )}
                    </div>
                  </div>
                )}

                {/* SHOW LOCKED SUCCESS STATE IF ALREADY SCHEDULED */}
                {result.requires_scheduling && isScheduled && (
                   <div style={{ marginTop: "20px", padding: "12px", background: "#ecfdf5", border: "1px solid #a7f3d0", color: "#065f46", borderRadius: "8px", fontWeight: "600", display: "flex", alignItems: "center", gap: "8px" }}>
                      <CheckCircle size={20} />
                      {scheduleStatus}
                   </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* TIMELINE + REPORT */}
        <div className="history-section">
          <div className="history-header">
            <h3>📊 Emotional Distribution (90 Days)</h3>
            <ReportDownload token={token} />
          </div>
          <p className="legend-hint">Bar chart shows total emotion occurrences over the period</p>
          <div className="chart-container">
            <EmotionBarChart history={history} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;