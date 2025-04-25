from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup

# 1. Crear la instancia
app = FastAPI()

# 2. Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Definir el endpoint después de crear app
@app.get("/analizar")
def analizar(keyword: str = Query(...), dominio: str = Query(...)):
    url = f"https://www.perplexity.ai/search?q={keyword.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    enlaces = [a["href"] for a in soup.find_all("a", href=True) if dominio in a["href"]]

    return {
        "keyword": keyword,
        "dominio": dominio,
        "aparece": len(enlaces) > 0,
        "enlaces_encontrados": enlaces
    }
