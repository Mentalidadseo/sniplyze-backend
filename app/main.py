from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/analizar")
def analizar(keyword: str = Query(...), dominio: str = Query(None)):
    query = keyword.replace(" ", "+")
    url = f"https://www.bing.com/search?q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    enlaces = [a["href"] for a in soup.select("li.b_algo h2 a[href]")]

    if dominio:
        enlaces_filtrados = [link for link in enlaces if dominio in link]
        aparece = len(enlaces_filtrados) > 0
        return {
            "keyword": keyword,
            "dominio": dominio,
            "aparece": aparece,
            "enlaces_encontrados": enlaces_filtrados
        }
    else:
        dominios = {}
        for link in enlaces:
            domain = urlparse(link).netloc
            if domain:
                dominios.setdefault(domain, []).append(link)
        return {
            "keyword": keyword,
            "dominios_encontrados": dominios
        }
