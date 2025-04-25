from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Habilitar CORS para permitir el acceso desde Bolt.new
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/analizar")
def analizar(keyword: str = Query(...), dominio: str = Query(None)):
    return {
        "keyword": keyword,
        "dominio": dominio,
        "aparece": True,
        "enlaces_encontrados": [
            "https://ejemplo.com/resultado1",
            "https://ejemplo.com/resultado2"
        ]
    }
