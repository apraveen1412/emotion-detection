# emotion-detection

Phase 0: Create a python virtual environment
    Dowload the model weight from the below link and copy the files in it to model folder in the project
        https://drive.google.com/drive/folders/1h1TI0fto4UNncoHa5_UA1C1IdE6kzWx2?usp=drive_link
    Navigate to the project root folder in terminal and run the following command
        python -m venv myenv
    This will create a python virtual environment and you need to activate the environment every time you open the project in IDE.
        ./myenv/Scripts/Activate.ps1
    This project uses google oauth so follow the steps for smooth ride
        1. Create a Google developer account, then create a Google Cloud project, enable Google Calendar API.
        3. Then goto credentials section and create an OAuth client (Desktop app).
        2. Download the JSON file, rename it to client_secret.json, and place it in backend/auth/.
        3. Then goto OAuth consent screen and then Audience, in test users add your email for calendar access.
        4. After that, calendar events are created automatically (do not delete auth/token.json).


Phase 1: Backend Setup & Run
    Navigate to the backend folder:
        cd backend

    Install all Python dependencies:
        pip install -r requirements.txt

    CRITICAL: Reset the Database
        Run this command to delete the old database (so the new User/Email tables can be created).
        If this is the first time running it, this command might fail, which is fine.
            del journal.db

    Start the Backend Server:
            uvicorn main:app --reload
        Keep this terminal open. You should see: Uvicorn running on http://0.0.0.0:8000



Phase 2: Frontend Setup & Run
    Open a new terminal window for this (keep the backend running in the first one).

    Navigate to the frontend folder:
            cd frontend
        Install React dependencies: (This installs React, Charts, Icons, etc.)
            npm install
        If you haven't saved the specific packages to package.json yet, run this instead:
            npm install chart.js react-chartjs-2 lucide-react
        Start the Frontend:
            npm start
        This will automatically open your browser to http://localhost:3000.