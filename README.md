# Messaging App

This repository contains a simple chat application that can be hosted as a **static site** on GitHub Pages.
> 🛑 **Important:** The code now requires a backend server (Flask example included) to provide shared storage.  
> The front‑end communicates with ` /api/...` endpoints; without a running server the app will not function beyond the login screen.

## Features

- Global user registration and login (email/password) backed by the Flask server
- Create and join named rooms; messages are visible to all room members
- Add friends by email and have automatic direct‑message rooms
- Send text messages and file attachments (stored on the server)
- Real‑time updates via polling (every 2 s) or opening multiple tabs
- Two‑panel layout: menu on the left, messaging area on the right


## Running the app (with Flask backend)

1. **Start the Flask server**
   ```sh
   cd backend
   python3 -m venv venv     # or use your virtualenv tool
   source venv/bin/activate
   pip install -r requirements.txt
   python app.py
   ```
   The server listens on `http://127.0.0.1:5000` by default and persists data in `backend/data.db`.

2. **Open the front‑end**
   - You can run `python3 -m http.server` from the top‑level directory and visit `http://localhost:8000`.
   - Alternatively, host the `index.html` on GitHub Pages; make sure to set `API_BASE` inside `app.js` to the URL where the Flask app is accessible.

3. **Use the site**
   - Register/login, create or join rooms, add friends, and send text/files.
   - All users hitting the same server will share messages in real time (clients poll every 2 s).

> The backend stores users, rooms, friends and message history in SQLite. Uploaded files are placed in `backend/uploads` and served by the Flask server.

## Why no external service?

GitHub Pages can only serve static files; there’s no capability to run server code.  
To have multiple users share messages in real time, you **must** use some backend (Firebase, a Node.js server, etc.) or a third‑party API.  
The local‑storage version is intended for offline demos or development when a backend isn’t available.

Feel free to switch back to the Firebase variant (commit history shows that version) if you ever gain access to a service.


## Development notes

- A simple Flask server with SQLite is provided in `backend/app.py`.  It uses Flask‑SQLAlchemy and basic session cookies.
- The front‑end `app.js` assumes the server provides `/api/*` endpoints as documented above.
- You can modify or extend both client and server to add authentication, permissions, or realtime websockets.

Enjoy building your global chat app!