#Running the Backend

uvicorn backend.strathy_app.app:app --reload --port 8000
uvicorn app:app --reload --port 8000

lOGIN
http://localhost:8000/oauth2/login

#Running the Front end
cd frontend
npm run dev
