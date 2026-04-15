Unzip and open folder in VS code.
Make new Bash terminal and Split bash terminal in VS code.
in terminal 1 (T1): cd frontend
in terminal 2 (T2): cd backend

Generate and Add API keys in .env file:
GEMINI_API_KEY=
GROQ_API_KEY=
ANTHROPIC_API_KEY=
SERPER_API_KEY=

in T2, start the backend: run these commands
`pip install -r requirements.txt`
`uvicorn api:app --reload`

in T1, run these commands:
`npm install`
`npm run dev`

Open browser and go to `http://localhost:3000`