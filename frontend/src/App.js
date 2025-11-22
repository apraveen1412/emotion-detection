import React, { useState, useEffect } from 'react';
import { Mic, Send, BookOpen, Activity, LogOut, Lock } from 'lucide-react';
import { Line } from 'react-chartjs-2';
import 'chart.js/auto';
import './App.css';

// Plutchik's Wheel inspired colors
const EMOTION_COLORS = {
  joy: '#FFD700', excitement: '#FFC107', amusement: '#FFB300', optimism: '#FF9800',
  gratitude: '#4CAF50', relief: '#8BC34A', admiration: '#CDDC39', caring: '#66BB6A',
  anger: '#F44336', annoyance: '#E91E63', fear: '#9C27B0', nervousness: '#BA68C8',
  sadness: '#2196F3', grief: '#3F51B5', disappointment: '#5C6BC0', remorse: '#7986CB',
  neutral: '#9E9E9E', surprise: '#00BCD4', curiosity: '#009688', confusion: '#607D8B'
};

const getColor = (emotion) => EMOTION_COLORS[emotion] || '#9E9E9E';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  
  // Auth State
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'signup'
  const [authError, setAuthError] = useState('');

  // App State
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (token) fetchHistory();
  }, [token]);

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setHistory([]);
    setResult(null);
    setUsername('');
    setPassword('');
    setEmail('');
  };

  // Helper function to perform login
  const performLogin = async () => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const res = await fetch('http://localhost:8000/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed');

    localStorage.setItem('token', data.access_token);
    setToken(data.access_token);
    setAuthError('');
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthError('');
    
    try {
      if (authMode === 'signup') {
        // 1. Attempt Signup
        const res = await fetch('http://localhost:8000/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, email, password })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Signup failed');

        // 2. If Signup successful, Auto-Login immediately
        await performLogin(); 

      } else {
        // Login Mode
        await performLogin();
      }
    } catch (err) {
      setAuthError(err.message);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch('http://localhost:8000/history', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.status === 401) logout();
      const data = await res.json();
      setHistory(data);
    } catch (e) { console.error(e); }
  };

  const handleAnalyze = async (audioBlob = null) => {
    setLoading(true);
    const date = new Date().toISOString().split('T')[0];
    const formData = new FormData();
    formData.append('date', date);

    let url = 'http://localhost:8000/analyze-text';
    if (audioBlob) {
      formData.append('file', audioBlob, 'recording.webm');
      url = 'http://localhost:8000/analyze-audio';
    } else {
      formData.append('text', text);
    }

    try {
      const response = await fetch(url, { 
        method: 'POST', 
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData 
      });
      
      if (response.status === 401) { logout(); return; }
      
      const data = await response.json();
      setResult(data);
      fetchHistory(); 
    } catch (err) {
      console.error(err);
      alert("Analysis failed. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    if (!navigator.mediaDevices) return alert("No mic access");
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    const chunks = [];
    recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: 'audio/webm' });
      stream.getTracks().forEach(t => t.stop());
      handleAnalyze(blob);
    };
    recorder.start();
    setMediaRecorder(recorder);
    setIsRecording(true);
  };

  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  // Graph Visualization
  const chartData = {
    labels: history.map(h => h.date),
    datasets: [{
      label: 'Emotion Timeline',
      // We map everything to a flat line (5) because the COLOR is the variable
      data: history.map(h => 5), 
      fill: false,
      borderColor: '#e5e7eb',
      borderWidth: 2,
      pointBackgroundColor: history.map(h => getColor(h.emotion)),
      pointRadius: 8,
      pointHoverRadius: 12,
    }]
  };

  // --- RENDER ---
  
  if (!token) {
    return (
      <div className="app-container auth-container">
        <div className="card auth-card">
          <div className="logo-header">🧠</div>
          <h1>MindJournal Safe</h1>
          <p>{authMode === 'login' ? 'Secure Login' : 'Create Private Profile'}</p>
          
          <form onSubmit={handleAuth}>
            <input 
              type="text" placeholder="Username" 
              value={username} onChange={e => setUsername(e.target.value)} 
              required 
            />
            
            {authMode === 'signup' && (
              <input 
                type="email" placeholder="Email Address" 
                value={email} onChange={e => setEmail(e.target.value)} 
                required 
              />
            )}

            <input 
              type="password" placeholder="Password" 
              value={password} onChange={e => setPassword(e.target.value)} 
              required 
            />
            
            <button type="submit" className="primary-btn full-width">
              {authMode === 'login' ? 'Log In' : 'Sign Up'}
            </button>
          </form>

          {authError && <div className="error-msg">{authError}</div>}
          
          <p className="toggle-text" onClick={() => {
            setAuthMode(authMode === 'login' ? 'signup' : 'login');
            setAuthError('');
            setEmail('');
          }}>
            {authMode === 'login' ? "New here? Create Account" : "Have an account? Log In"}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <div className="main-card">
        <header className="app-header">
          <div>
            <h1>🧠 MindJournal</h1>
            <p className="user-badge">Logged in as: <strong>{username}</strong></p>
          </div>
          <button onClick={logout} className="icon-btn logout-btn" title="Logout">
            <LogOut size={18}/> Logout
          </button>
        </header>

        <div className="input-section">
          <textarea 
            value={text} 
            onChange={(e) => setText(e.target.value)}
            placeholder="How was your day? Type here or record your voice..."
          />
          <div className="controls">
            <button 
              className={`icon-btn ${isRecording ? 'recording' : ''}`} 
              onClick={isRecording ? stopRecording : startRecording}
            >
              <Mic /> {isRecording ? 'Stop' : 'Record Voice'}
            </button>
            <button 
              className="primary-btn" 
              onClick={() => handleAnalyze()} 
              disabled={loading || (!text && !isRecording)}
            >
              {loading ? 'Analyzing...' : 'Analyze Entry'} <Send size={16} />
            </button>
          </div>
        </div>

        {result && (
          <div className="result-section" style={{borderLeft: `6px solid ${getColor(result.emotion)}`}}>
            <div className="emotion-badge">
              <h2 style={{color: getColor(result.emotion)}}>{result.emotion.toUpperCase()}</h2>
              <span className="confidence-pill">{result.score}% Confidence</span>
            </div>
            {result.transcription && <div className="transcription"><strong>You said:</strong> "{result.transcription}"</div>}
            <div className="insight-box">
              <h3><BookOpen size={18}/> Scientific Insight</h3>
              <p>{result.insight}</p>
            </div>
          </div>
        )}

        <div className="history-section">
          <h3><Activity size={18}/> Emotional Journey (90 Days)</h3>
          <p className="legend-hint">Colors represent different emotions based on Plutchik's Wheel</p>
          <div className="chart-container">
            <Line 
              data={chartData} 
              options={{ 
                maintainAspectRatio: false,
                scales: { y: { display: false }, x: { grid: { display: false } } },
                plugins: { tooltip: { callbacks: { label: (ctx) => `Emotion: ${history[ctx.dataIndex].emotion}` } } }
              }} 
            />
          </div>
          <div className="legend">
             <span style={{color: EMOTION_COLORS.joy}}>● Joy</span>
             <span style={{color: EMOTION_COLORS.anger}}>● Anger</span>
             <span style={{color: EMOTION_COLORS.sadness}}>● Sadness</span>
             <span style={{color: EMOTION_COLORS.fear}}>● Fear</span>
             <span style={{color: EMOTION_COLORS.neutral}}>● Neutral</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;