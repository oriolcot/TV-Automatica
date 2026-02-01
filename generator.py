import requests
from datetime import datetime, timedelta

# URL de l'API
API_URL = "https://api.cdn-live.tv/api/v1/events/sports/?user=cdnlivetv&plan=free"

# Diccionari de Banderes
BANDERES = {
    "es": "🇪🇸", "mx": "🇲🇽", "ar": "🇦🇷", "gb": "🇬🇧", "uk": "🇬🇧", "us": "🇺🇸", 
    "ca": "🇨🇦", "it": "🇮🇹", "fr": "🇫🇷", "de": "🇩🇪", "pt": "🇵🇹", "br": "🇧🇷",
    "nl": "🇳🇱", "tr": "🇹🇷", "pl": "🇵🇱", "ru": "🇷🇺", "ua": "🇺🇦", "hr": "🇭🇷",
    "rs": "🇷🇸", "gr": "🇬🇷", "ro": "🇷🇴", "cz": "🇨🇿", "se": "🇸🇪", "no": "🇳🇴",
    "dk": "🇩🇰", "fi": "🇫🇮", "bg": "🇧🇬", "il": "🇮🇱"
}

def arreglar_hora(hora_str):
    try:
        data_hora = datetime.strptime(hora_str, "%H:%M")
        nova_hora = data_hora + timedelta(hours=1) # Sumem 1 hora
        return nova_hora.strftime("%H:%M")
    except:
        return hora_str

def main():
    try:
        print("Descarregant dades...")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"}
        response = requests.get(API_URL, headers=headers, timeout=15)
        data = response.json()
        matches = data.get("cdn-live-tv", {}).get("Soccer", [])
        
        # INICI DEL CODI HTML (ESTIL FOSC PER A TV)
        html_content = """
        <!DOCTYPE html>
        <html lang="ca">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Futbol TV</title>
            <style>
                body { background-color: #121212; color: #ffffff; font-family: sans-serif; margin: 0; padding: 20px; }
                h1 { text-align: center; color: #00e676; margin-bottom: 30px; }
                .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
                .card { background-color: #1e1e1e; border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
                .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px; border-bottom: 1px solid #333; padding-bottom: 10px; }
                .time { font-size: 1.2em; font-weight: bold; color: #00e676; background: #333; padding: 5px 10px; border-radius: 5px; }
                .teams { font-size: 1.1em; font-weight: bold; margin-left: 10px; flex-grow: 1; }
                .channels { display: flex; flex-wrap: wrap; gap: 10px; }
                .btn { 
                    display: inline-block; text-decoration: none; color: white; 
                    background-color: #333; padding: 10px 15px; border-radius: 8px; 
                    font-size: 0.9em; transition: background 0.2s; border: 1px solid #444;
                }
                .btn:hover { background-color: #00e676; color: black; border-color: #00e676; }
                .flag { margin-right: 5px; font-size: 1.2em; }
                .no-partits { text-align: center; margin-top: 50px; font-size: 1.5em; color: #777; }
                .footer { text-align: center; margin-top: 40px; color: #555; font-size: 0.8em; }
            </style>
        </head>
        <body>
            <h1>⚽ Partits en Directe</h1>
            <div class="grid">
        """

        if not matches:
            html_content += '<div class="no-partits">No hi ha partits ara mateix 😴</div>'

        for match in matches:
            home = match.get('homeTeam', 'Home')
            away = match.get('awayTeam', 'Away')
            hora = arreglar_hora(match.get('time', '00:00'))
            
            # Creem la targeta del partit
            html_content += f"""
            <div class="card">
                <div class="header">
                    <span class="time">{hora}</span>
                    <span class="teams">{home} vs {away}</span>
                </div>
                <div class="channels">
            """
            
            # Afegim els botons dels canals
            for channel in match.get('channels', []):
                name = channel.get('channel_name', 'Canal')
                url = channel.get('url', '#')
                code = channel.get('channel_code', '').lower()
                bandera = BANDERES.get(code, "🌍") # Si no troba bandera, posa un món
                
                html_content += f"""
                    <a href="{url}" class="btn" target="_self">
                        <span class="flag">{bandera}</span> {name}
                    </a>
                """
            
            html_content += """
                </div>
            </div>
            """

        # Finalitzem l'HTML
        html_content += f"""
            </div>
            <div class="footer">Última actualització: {datetime.now().strftime('%H:%M')}</div>
        </body>
        </html>
        """

        # Guardem com a index.html perquè sigui la portada de la web
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print("ÈXIT: Web generada correctament (index.html)")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()