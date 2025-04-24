import requests
from bs4 import BeautifulSoup

def analizar_perplexity(keyword: str, dominio: str = None):
    query = keyword.replace(' ', '+')
    url = f"https://www.perplexity.ai/search?q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return {"error": f"Error {response.status_code} al consultar Perplexity"}

        soup = BeautifulSoup(response.text, 'html.parser')
        enlaces = [a['href'] for a in soup.find_all('a', href=True)
                   if a['href'].startswith("http") and "perplexity" not in a['href']]

        aparece = any(dominio in enlace for enlace in enlaces) if dominio else False

        return {
            "keyword": keyword,
            "dominio": dominio,
            "aparece": aparece,
            "enlaces_encontrados": enlaces
        }

    except Exception as e:
        return {"error": str(e)}