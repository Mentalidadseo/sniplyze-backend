from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Permitir peticiones desde cualquier origen (como Bolt.new)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # O usa ["https://bolt.new"] para limitarlo solo a Bolt
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
