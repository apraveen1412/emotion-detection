import React, { useState, useEffect, useRef } from "react";
import { Mic, Send, LogOut, Calendar, Settings, X, CheckCircle } from "lucide-react";
import "./App.css";
// encryptText removed - send plaintext; AI must read it before any encryption

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

const SECURITY_QUESTIONS = [
  "What was the name of your first pet?",
  "What is your mother's maiden name?",
  "What city were you born in?",
  "What was your childhood nickname?",
  "What is the name of your favorite childhood friend?"
];

function App() {
  /* ---------- AUTH STATE ---------- */
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [authMode, setAuthMode] = useState("login"); // 'login', 'signup', 'forgot'
  const [identifier, setIdentifier] = useState(""); 
  const [email, setEmail] = useState(""); 
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [authSuccess, setAuthSuccess] = useState("");

  // Forgot Password State
  const [forgotStep, setForgotStep] = useState(1);
  const [retrievedQuestion, setRetrievedQuestion] = useState("");
  const [securityAnswer, setSecurityAnswer] = useState("");
  const [resetNewPassword, setResetNewPassword] = useState(""); // separate from settings newPassword

  /* ---------- APP & PROFILE STATE ---------- */
  const [profile, setProfile] = useState({ username: "", email: "", has_security_question: false });
  const [showProfile, setShowProfile] = useState(false);
  const [morningTime, setMorningTime] = useState("06:00");
  const [eveningTime, setEveningTime] = useState("17:00");
  
  // Settings Inputs
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [selectedQuestion, setSelectedQuestion] = useState(SECURITY_QUESTIONS[0]);
  const [newAnswer, setNewAnswer] = useState("");
  const [settingsMsg, setSettingsMsg] = useState("");

  // Settings UI Toggles
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [isPasswordVerified, setIsPasswordVerified] = useState(false); 
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");

  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);

  const [scheduledTime, setScheduledTime] = useState("");
  const [scheduleStatus, setScheduleStatus] = useState("");
  const [isScheduled, setIsScheduled] = useState(false);
  const [countdown, setCountdown] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    if (token) { fetchTimeline(); fetchProfile(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (countdown === null) return;
    if (countdown === 0) { handleSchedule("auto"); setCountdown(null); return; }
    timerRef.current = setTimeout(() => setCountdown((prev) => prev - 1), 1000);
    return () => clearTimeout(timerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [countdown]);

  /* -------------------- PROFILE / SETTINGS -------------------- */
  const fetchProfile = async () => {
    try {
      const res = await fetch("http://localhost:8000/profile", { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        setProfile(data);
        setMorningTime(data.default_morning_time);
        setEveningTime(data.default_evening_time);
      }
    } catch (err) { console.error(err); }
  };

  const saveTimes = async () => {
    const res = await fetch("http://localhost:8000/profile", {
      method: "PUT", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ default_morning_time: morningTime, default_evening_time: eveningTime })
    });
    setSettingsMsg(res.ok ? "Times saved!" : "Error saving times.");
    setTimeout(() => setSettingsMsg(""), 3000);
  };

  const saveSecurityQuestion = async () => {
    if (!newAnswer) return setSettingsMsg("Answer cannot be empty.");
    const res = await fetch("http://localhost:8000/profile/security-question", {
      method: "PUT", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ question: selectedQuestion, answer: newAnswer })
    });
    if (res.ok) {
      setSettingsMsg("Security question updated!");
      setProfile({...profile, has_security_question: true});
      setNewAnswer("");
    } else { setSettingsMsg("Failed to update question."); }
    setTimeout(() => setSettingsMsg(""), 3000);
  };

  const verifyCurrentPassword = async () => {
    if (!currentPassword) return setSettingsMsg("Please enter your current password.");
    const res = await fetch("http://localhost:8000/profile/verify-password", {
      method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ password: currentPassword })
    });
    if (res.ok) {
      setIsPasswordVerified(true);
      setSettingsMsg("");
    } else {
      setSettingsMsg("Incorrect current password.");
      setTimeout(() => setSettingsMsg(""), 3000);
    }
  };

  const changePassword = async () => {
    if (!newPassword) return setSettingsMsg("Please enter a new password.");
    const res = await fetch("http://localhost:8000/profile/password", {
      method: "PUT", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
    });
    if (res.ok) {
      setSettingsMsg("Password successfully changed!");
      setCurrentPassword(""); setNewPassword("");
      setShowPasswordChange(false);
      setIsPasswordVerified(false);
    } else {
      const data = await res.json();
      setSettingsMsg(data.detail || "Error changing password.");
    }
    setTimeout(() => setSettingsMsg(""), 3000);
  };

  const downloadAllData = async () => {
    try {
      const res = await fetch(`http://localhost:8000/report/excel?range=yearly`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Download failed");
      const data = await res.json();
      
      const byteCharacters = atob(data.content);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);

      const blob = new Blob([byteArray], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = data.filename.replace("yearly", "all_data");
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setSettingsMsg("Error downloading data.");
      setTimeout(() => setSettingsMsg(""), 3000);
    }
  };

  const deleteAccount = async () => {
    if (!deletePassword) return setSettingsMsg("Please enter your password to confirm.");
    const res = await fetch("http://localhost:8000/profile/account", {
      method: "DELETE", 
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ password: deletePassword })
    });
    if (res.ok) {
      alert("Account deleted. We are sorry to see you go.");
      logout();
    } else {
      const data = await res.json();
      setSettingsMsg(data.detail || "Incorrect password.");
      setTimeout(() => setSettingsMsg(""), 3000);
    }
  };

  /* -------------------- AUTH & FORGOT PASSWORD -------------------- */
  const logout = () => {
    localStorage.clear(); setToken(null); setProfile({}); setHistory([]); setResult(null); setCountdown(null); setIsScheduled(false);
  };

  const handleAuth = async (e) => {
    e.preventDefault(); setAuthError(""); setAuthSuccess("");
    try {
      if (authMode === "signup") {
        const res = await fetch("http://localhost:8000/signup", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: identifier, email: email, password: password }),
        });
        if (!res.ok) throw new Error((await res.json()).detail);
      }
      const formData = new URLSearchParams();
      formData.append("username", identifier);
      formData.append("password", password);
      const res = await fetch("http://localhost:8000/token", { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);
    } catch (err) { setAuthError(err.message); }
  };

  const getSecurityQuestion = async (e) => {
    e.preventDefault(); setAuthError(""); setAuthSuccess("");
    const res = await fetch("http://localhost:8000/forgot-password/question", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier })
    });
    const data = await res.json();
    if (!res.ok) return setAuthError(data.detail);
    setRetrievedQuestion(data.question);
    setForgotStep(2);
  };

  const resetPassword = async (e) => {
    e.preventDefault(); setAuthError("");
    const res = await fetch("http://localhost:8000/forgot-password/reset", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, answer: securityAnswer, new_password: resetNewPassword })
    });
    const data = await res.json();
    if (!res.ok) return setAuthError(data.detail);
    setAuthSuccess("Password reset successful! Please log in.");
    setAuthMode("login"); setForgotStep(1); setPassword(""); setResetNewPassword(""); setSecurityAnswer("");
  };

  /* -------------------- ANALYSIS -------------------- */
  const fetchTimeline = async () => {
    const res = await fetch("http://localhost:8000/timeline", { headers: { Authorization: `Bearer ${token}` } });
    if (res.ok) setHistory(await res.json());
  };

  const handleAnalyze = async (audioBlob = null) => {
    setLoading(true); setScheduleStatus(""); setCountdown(null); setIsScheduled(false); 
    const formData = new FormData(); formData.append("date", new Date().toISOString().split("T")[0]);
    if (audioBlob) {
      formData.append("file", audioBlob, "voice.webm");
    } else {
      formData.append("text", text); // plaintext - backend AI analyzes this
    }
    const url = audioBlob ? "http://localhost:8000/analyze-audio" : "http://localhost:8000/analyze-text";
    try {
      const res = await fetch(url, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: formData });
      if (res.status === 401) return logout();
      const data = await res.json();
      setResult(data); setText(""); fetchTimeline();
      if (data.requires_scheduling) setCountdown(30);
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream); const chunks = [];
    recorder.ondataavailable = (e) => chunks.push(e.data);
    recorder.onstop = () => { stream.getTracks().forEach(t => t.stop()); handleAnalyze(new Blob(chunks, { type: "audio/webm" })); };
    recorder.start(); setMediaRecorder(recorder); setIsRecording(true);
  };
  const stopRecording = () => { if (mediaRecorder) { mediaRecorder.stop(); setIsRecording(false); } };

  const handleSchedule = async (timeMode = null) => {
    if (timeMode !== "auto") setCountdown(null);
    const timeToSubmit = timeMode === "auto" ? "auto" : scheduledTime;
    if (!timeToSubmit || !result?.suggestion) return;
    setScheduleStatus("Scheduling...");
    const formattedSuggestion = `OBSERVATION:\n${result.suggestion.observation}\n\nINSIGHTS:\n${result.suggestion.insight}\n\nACTIONABLE STEP:\n${result.suggestion.action}`;
    const formData = new FormData(); formData.append("suggestion", formattedSuggestion); formData.append("scheduled_time", timeToSubmit);
    const res = await fetch("http://localhost:8000/schedule-activity", { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: formData });
    const data = await res.json();
    if (res.ok) { setScheduleStatus(`✅ ${data.message}`); setIsScheduled(true); } else { setScheduleStatus("❌ Failed to schedule"); }
  };

  /* ===================== AUTH UI ===================== */
  if (!token) {
    return (
      <div className="app-container auth-container">
        <div className="auth-card">
          <div className="logo-header">🧠</div>
          <h1>Intelligent Emotion Recognition and Reminder System</h1>
          {authSuccess && <p style={{color: '#059669', fontWeight: 'bold'}}>{authSuccess}</p>}
          
          {authMode === "forgot" ? (
             <form onSubmit={forgotStep === 1 ? getSecurityQuestion : resetPassword}>
                <p>Reset Password</p>
                {forgotStep === 1 && (
                  <>
                    <input type="text" placeholder="Username or Email" value={identifier} onChange={(e) => setIdentifier(e.target.value)} required />
                    <button type="submit" className="primary-btn full-width">Get Security Question</button>
                  </>
                )}
                {forgotStep === 2 && (
                  <>
                    <p style={{color: '#4f46e5', fontWeight: 'bold', margin: '0 0 10px 0'}}>{retrievedQuestion}</p>
                    <input type="text" placeholder="Your Answer" value={securityAnswer} onChange={(e) => setSecurityAnswer(e.target.value)} required />
                    <input type="password" placeholder="New Password" value={resetNewPassword} onChange={(e) => setResetNewPassword(e.target.value)} required />
                    <button type="submit" className="primary-btn full-width">Reset Password</button>
                  </>
                )}
             </form>
          ) : (
             <form onSubmit={handleAuth}>
              <p>{authMode === "login" ? "Login to your account" : "Create an Account"}</p>
              <input type="text" placeholder="Username" value={identifier} onChange={(e) => setIdentifier(e.target.value)} required />
              {authMode === "signup" && <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />}
              <input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              <button type="submit" className="primary-btn full-width">{authMode === "login" ? "Log In" : "Sign Up"}</button>
            </form>
          )}

          {authError && <div className="error-msg">{authError}</div>}
          
          <div style={{display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '24px', width: '100%'}}>
            <span className="toggle-text" style={{marginTop: 0}} onClick={() => {setAuthMode(authMode === "login" ? "signup" : "login"); setAuthSuccess(""); setAuthError(""); setForgotStep(1);}}>
              {authMode === "login" ? "New here? Create Account" : authMode === "signup" ? "Have an account? Log In" : "Back to Login"}
            </span>
            {authMode !== "forgot" && (
              <span className="toggle-text" style={{color: '#6b7280'}} onClick={() => {setAuthMode("forgot"); setForgotStep(1); setAuthError("");}}>
                Forgot Password?
              </span>
            )}
          </div>
        </div>
      </div>
    );
  }

  /* ===================== MAIN UI ===================== */
  return (
    <div className="app-container">
      {/* OVERLAY FOR SETTINGS */}
      {showProfile && <div className="modal-overlay" onClick={() => setShowProfile(false)}></div>}
      
      {showProfile && (
        <div className="settings-modal">
           <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
              <h2 style={{ margin: 0 }}>⚙️ Account Settings</h2>
              <button onClick={() => { setShowProfile(false); setShowPasswordChange(false); setIsPasswordVerified(false); setShowDeleteConfirm(false); setCurrentPassword(""); setNewPassword(""); }} className="icon-btn"><X size={18}/></button>
           </div>
           
           {settingsMsg && <div style={{background: '#e0e7ff', color: '#4338ca', padding: '10px', borderRadius: '8px', marginBottom: '20px', fontWeight: 'bold', textAlign: 'center'}}>{settingsMsg}</div>}

           <div className="settings-section">
             <h3>Profile Details</h3>
             <div className="profile-detail"><span>Username:</span> <strong>{profile.username}</strong></div>
             <div className="profile-detail"><span>Email:</span> <strong>{profile.email}</strong></div>
           </div>

           <div className="settings-section">
             <h3>Security Question (For Password Reset)</h3>
             {profile.has_security_question && <p style={{color: '#059669', fontSize: '0.85rem', marginBottom: '10px'}}>✅ You have a security question set. Submitting below will overwrite it.</p>}
             <select value={selectedQuestion} onChange={(e) => setSelectedQuestion(e.target.value)}>
               {SECURITY_QUESTIONS.map(q => <option key={q} value={q}>{q}</option>)}
             </select>
             <input type="text" placeholder="Your Secret Answer" value={newAnswer} onChange={(e) => setNewAnswer(e.target.value)} style={{marginTop: '10px'}}/>
             <button onClick={saveSecurityQuestion} className="primary-btn" style={{marginTop: '10px'}}>Save Security Question</button>
           </div>

           <div className="settings-section">
             <h3>Change Password</h3>
             {!showPasswordChange ? (
                <button onClick={() => setShowPasswordChange(true)} className="primary-btn">Change Password</button>
             ) : !isPasswordVerified ? (
                <>
                  <input type="password" placeholder="Enter Current Password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
                  <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
                    <button onClick={verifyCurrentPassword} className="primary-btn">Verify Password</button>
                    <button onClick={() => {setShowPasswordChange(false); setCurrentPassword(""); setSettingsMsg("");}} className="icon-btn">Cancel</button>
                  </div>
                </>
             ) : (
                <>
                  <p style={{color: '#059669', fontSize: '0.85rem', marginBottom: '10px'}}>✅ Password verified.</p>
                  <input type="password" placeholder="Enter New Password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
                  <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
                    <button onClick={changePassword} className="primary-btn">Update Password</button>
                    <button onClick={() => {setShowPasswordChange(false); setIsPasswordVerified(false); setCurrentPassword(""); setNewPassword(""); setSettingsMsg("");}} className="icon-btn">Cancel</button>
                  </div>
                </>
             )}
           </div>

           <div className="settings-section">
             <h3>Scheduling Preferences</h3>
             <p style={{ color: "#4b5563", fontSize: '0.9rem', marginBottom: "15px" }}>If you don't pick a specific time, Intelligent Emotion Recognition and Reminder System will automatically schedule activities for the closest upcoming default time.</p>
             <label style={{ display: "block", fontWeight: "bold", marginBottom: "8px" }}>Default Morning Schedule</label>
             <input type="time" value={morningTime} onChange={(e) => setMorningTime(e.target.value)} style={{ marginBottom: "20px" }}/>
             <label style={{ display: "block", fontWeight: "bold", marginBottom: "8px" }}>Default Evening Schedule</label>
             <input type="time" value={eveningTime} onChange={(e) => setEveningTime(e.target.value)} style={{ marginBottom: "20px" }}/>
             <button onClick={saveTimes} className="primary-btn">Save Preferences</button>
           </div>

           <div className="settings-section" style={{borderColor: '#fca5a5', background: '#fef2f2'}}>
             <h3 style={{color: '#ef4444', borderBottomColor: '#fca5a5'}}>Danger Zone</h3>
             <p style={{fontSize: '0.9rem', color: '#7f1d1d', marginBottom: '15px'}}>Once you delete your account, there is no going back. Please download your data from the dashboard first.</p>
             
             <div style={{ display: "flex", gap: "10px" }}>
               <button onClick={downloadAllData} className="icon-btn" style={{ flex: 1, justifyContent: 'center' }}>Download Data</button>
               {!showDeleteConfirm && (
                 <button onClick={() => setShowDeleteConfirm(true)} className="danger-btn" style={{ marginTop: 0, flex: 1 }}>Delete Account</button>
               )}
             </div>

             {showDeleteConfirm && (
               <div style={{ marginTop: "15px" }}>
                 <input type="password" placeholder="Enter password to confirm deletion" value={deletePassword} onChange={(e) => setDeletePassword(e.target.value)} />
                 <div style={{ display: "flex", gap: "10px", marginTop: "10px" }}>
                   <button onClick={deleteAccount} className="danger-btn" style={{ marginTop: 0, flex: 1 }}>Confirm Delete</button>
                   <button onClick={() => {setShowDeleteConfirm(false); setDeletePassword(""); setSettingsMsg("");}} className="icon-btn" style={{ flex: 1, justifyContent: 'center' }}>Cancel</button>
                 </div>
               </div>
             )}
           </div>
        </div>
      )}

      <div className="main-card">
        <header className="app-header">
          <div className="app-header-left">
            <h1>Intelligent Emotion Recognition and Reminder System</h1>
            <p className="user-badge">Logged in as {profile.username || "Loading..."}</p>
          </div>
          <div className="app-header-actions">
            <button onClick={() => setShowProfile(true)} className="icon-btn">
              <Settings size={16} /><span className="btn-label"> Settings</span>
            </button>
            <button onClick={logout} className="icon-btn">
              <LogOut size={16} /><span className="btn-label"> Logout</span>
            </button>
          </div>
        </header>

        <div className="input-section">
          <textarea value={text} placeholder="How was your day?" onChange={(e) => setText(e.target.value)} 
            onInput={(e) => { e.target.style.height = "auto"; e.target.style.height = e.target.scrollHeight + "px"; }}
          />
          <div className="controls">
            <button className={`icon-btn ${isRecording ? "recording" : ""}`} onClick={isRecording ? stopRecording : startRecording}>
              <Mic /> {isRecording ? "Stop" : "Record"}
            </button>
            <button className="primary-btn" onClick={() => handleAnalyze()} disabled={loading || isRecording || !text}>
              {loading ? "Analyzing..." : "Analyze"} <Send size={16} />
            </button>
          </div>
        </div>

        {result?.emotions && (
          <div className="result-section" style={{ borderLeft: `6px solid ${result.emotions[0] ? getColor(result.emotions[0]) : "#9E9E9E"}` }}>
            {result.input_text && <div style={{ marginBottom: "15px", fontStyle: "italic", background: "#f3f4f6", padding: "12px", borderRadius: "8px" }}>"{result.input_text}"</div>}
            <h2>{result.emotions.map((emo, idx) => <span key={emo} style={{ color: getColor(emo), marginRight: "6px", textTransform: "uppercase" }}>{emo}{idx < result.emotions.length - 1 ? "," : ""}</span>)}</h2>

            {result.suggestion && result.suggestion.observation && (
              <div className="suggestion-box">
                <h3 style={{ marginTop: 0, borderBottom: "1px solid #e5e7eb", paddingBottom: "10px", fontSize: "1.1rem" }}>📋 Suggestions</h3>
                <div style={{ margin: "16px 0" }}><strong style={{ color: "#4f46e5", display: "block", marginBottom: "4px" }}>Observation</strong><p style={{ margin: 0, lineHeight: "1.5" }}>{result.suggestion.observation}</p></div>
                <div style={{ margin: "16px 0" }}><strong style={{ color: "#4f46e5", display: "block", marginBottom: "4px" }}>Insight</strong><p style={{ margin: 0, lineHeight: "1.5" }}>{result.suggestion.insight}</p></div>
                <div style={{ margin: "16px 0" }}><strong style={{ color: "#4f46e5", display: "block", marginBottom: "4px" }}>Actionable Step</strong><p style={{ margin: 0, lineHeight: "1.5" }}>{result.suggestion.action}</p></div>

                {result.requires_scheduling && !isScheduled && (
                  <div style={{ marginTop: "20px", borderTop: "1px solid #e5e7eb", paddingTop: "15px" }}>
                    {countdown !== null && (
                      <div style={{ background: "#fef3c7", color: "#d97706", padding: "10px", borderRadius: "8px", display: "flex", justifyContent: "space-between", marginBottom: '10px', fontWeight: 'bold' }}>
                        <span>⏱️ Auto-scheduling in {countdown}s...</span>
                        <button onClick={() => setCountdown(null)} style={{ background: "transparent", border: "none", color: "#92400e", cursor: "pointer", fontWeight: "bold" }}>Cancel</button>
                      </div>
                    )}
                    <div style={{ display: "flex", gap: "10px", alignItems: "center", background: "#f9fafb", padding: "12px", borderRadius: "8px", flexWrap: "wrap" }}>
                        <Calendar size={18} color="#6b7280" />
                        <input type="datetime-local" value={scheduledTime} onChange={(e) => { setScheduledTime(e.target.value); setCountdown(null); }} style={{ padding: "8px", borderRadius: "6px", border: "1px solid #d1d5db" }}/>
                        <button onClick={() => handleSchedule()} disabled={!scheduledTime || scheduleStatus.includes("Scheduling")} className="primary-btn">Pick Custom Time</button>
                        {scheduleStatus && !scheduleStatus.includes("✅") && <span style={{ color: "#ef4444", fontWeight: "600" }}>{scheduleStatus}</span>}
                    </div>
                  </div>
                )}
                {result.requires_scheduling && isScheduled && (
                   <div style={{ marginTop: "20px", padding: "12px", background: "#ecfdf5", color: "#065f46", borderRadius: "8px", display: "flex", alignItems: "center", gap: "8px", fontWeight: "bold" }}><CheckCircle size={20} />{scheduleStatus}</div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="history-section">
          <div className="history-header">
            <h3>📊 Emotional Distribution (90 Days)</h3>
            <ReportDownload token={token} />
          </div>
          <p className="legend-hint">Bar chart shows total emotion occurrences over the period</p>
          <div className="chart-container"><EmotionBarChart history={history} /></div>
        </div>
      </div>
    </div>
  );
}
export default App;