This document explains **step-by-step** how to set up and run the **Emotion Detection** project on a local machine.

Follow the phases **in order**. Do not skip steps.

---

## 📌 Prerequisites (Before You Start)

Make sure the following are installed on your system:

- **Python 3.9+**
- **Node.js (v16 or above)**
- **npm**
- **Git**
- **Internet connection** (for model download & Google OAuth)

---

## 📂 Project Structure (Overview)

```
emotion-detection/
│
├── backend/
│   ├── auth/
│   │   ├── client_secret.json
│   │   └── token.json
│   ├── model/
│   ├── journal.db
│   └── main.py
│
├── frontend/
│   └── package.json
│
├── myenv/          (created later)
└── README.md

```

---

# Phase 0: Initial Setup (VERY IMPORTANT)

### 0.1 Download Model Weights

This project **does NOT train the model at runtime**.

You must manually download the trained model weights.

1. Open the link below in your browser:
    
    👉 https://drive.google.com/drive/folders/1h1TI0fto4UNncoHa5_UA1C1IdE6kzWx2?usp=drive_link
    
2. Download **all files** from the Drive folder.
3. Copy **all downloaded files** into:
    
    ```
    backend/model/
    
    ```
    

Note: **Do not rename or modify any model files.**

---

### 0.2 Create Python Virtual Environment

1. Open a terminal in the **project root folder**:
    
    ```
    emotion-detection/
    
    ```
    
2. Create a virtual environment:
    
    ```bash
    python -m venv myenv
    ```
    
3. Activate the virtual environment (Windows – PowerShell):
    
    ```powershell
    ./myenv/Scripts/Activate.ps1
    ```
    

You must **activate this environment every time** you work on the backend.

---

## Phase 0.3: Google OAuth & Calendar Setup

This project uses **Google Calendar API** for creating reminders.

### Step-by-step Google Setup

1. Go to **Google Cloud Console**
2. Create a **new project**
3. Enable **Google Calendar API**
4. Go to **APIs & Services → Credentials**
5. Create credentials:
    - Type: **OAuth Client ID**
    - Application type: **Desktop App**
6. Download the OAuth JSON file
7. Rename it to:
    
    ```
    client_secret.json
    ```
    
8. Place it inside:
    
    ```
    backend/auth/
    ```
    

---

### OAuth Consent Screen Setup

1. Go to **OAuth consent screen**
2. Select **External**
3. Fill required basic details
4. Go to **Audience**
5. Under **Test Users**, add your Gmail ID

 **Important Notes**

- Do NOT delete `backend/auth/token.json`
- Calendar events are created automatically after first login
- App is in **testing mode**, so only test users will work

---

# Phase 1: Backend Setup & Run

### 1.1 Navigate to Backend

```bash
cd backend
```

---

### 1.2 Install Python Dependencies

Make sure virtual environment is active.

```bash
pip install -r requirements.txt
```

---

### 1.3 Reset Database (CRITICAL STEP)

This ensures correct table creation.

```powershell
del journal.db
```

 Notes:

- If the file does not exist, an error may appear — **this is OK**
- This is required when running the project fresh

---

### 1.4 Start Backend Server

```bash
uvicorn main:app --reload
```

You should see:

```
Uvicorn running on http://0.0.0.0:8000
```

✅ **Keep this terminal OPEN**

❌ Do NOT stop the backend while running frontend

---

# Phase 2: Frontend Setup & Run

### 2.1 Open a New Terminal

Keep backend running in the first terminal.

---

### 2.2 Navigate to Frontend

```bash
cd frontend
```

---

### 2.3 Install Frontend Dependencies

```bash
npm install
```

If packages are missing, run:

```bash
npm install chart.js react-chartjs-2 lucide-react
```

---

### 2.4 Start Frontend Server

```bash
npm start
```

This will open:

```
http://localhost:3000
```

---

# ✅ Final Check (Everything Working)

- Backend running at `http://localhost:8000`
- Frontend running at `http://localhost:3000`
- Emotion detection works for text & speech
- Emotion trends appear
- Google Calendar events trigger for negative emotions

---

## ⚠️ Common Mistakes to Avoid

- ❌ Forgetting to activate virtual environment
- ❌ Missing model files in `backend/model/`
- ❌ Deleting `token.json`
- ❌ Running frontend before backend
- ❌ Using unapproved Google account
