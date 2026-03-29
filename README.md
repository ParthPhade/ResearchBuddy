# ResearchBuddy

ResearchBuddy is an AI-powered tool designed to help students understand research papers quickly and easily.

## Features
- **PDF Summarization:** Upload a research paper and get a concise summary of its core components.
- **AI-Driven Insights:** Powered by Google's Gemini Flash model for fast and accurate understanding.

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js & npm

### Backend Setup
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment:
   ```bash
   py -m venv venv
   source venv/Scripts/activate # On Windows use `venv\Scripts\activate`
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `backend` directory and add your Google API key:
   ```env
   GOOGLE_API_KEY=your_api_key_here
   ```
5. Start the backend server:
   ```bash
   python main.py
   ```
   The API will be available at `http://localhost:8000`.

### Frontend Setup
1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the React development server:
   ```bash
   npm start
   ```
   The application will be available at `http://localhost:3000`.

## CLI Usage
ResearchBuddy also comes with a command-line interface for quick summarization.

### CLI Setup
1.  Install CLI dependencies:
    ```bash
    pip install requests google-auth-oauthlib
    ```
2.  **Google Auth Setup:**
    -   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    -   Create a new project and enable the "Google People API".
    -   Create **OAuth 2.0 Client IDs** (Application type: Desktop App).
    -   Download the JSON file and rename it to `client_secrets.json` in the `ResearchBuddy` directory.
3.  **Login:**
    ```bash
    python cli.py login
    ```
4.  **Summarize a paper:**
    ```bash
    python cli.py summarize path/to/paper.pdf
    ```

## Authentication Options
ResearchBuddy supports three ways to handle API keys:
1.  **Direct API Key:** Provide your key in the Frontend Settings.
2.  **Google Authentication:** Log in via the CLI/Frontend (Coming soon to Frontend). The backend will use its own API key to serve authenticated users.
3.  **Server-side Key:** Set `GEMINI_API_KEY` in the backend `.env` file (not recommended for public use without auth).
