import requests
from datetime import datetime, timedelta

# URL de l'API
API_URL = "https://api.cdn-live.tv/api/v1/events/sports/?user=cdnlivetv&plan=free"

def arreglar_hora(hora_str):
    try:
        data_hora = datetime.strptime(hora_str, "%H:%M")
        # SUMA 1 HORA (Ajusta això segons calgui)
        nova_hora = data_hora + timedelta(hours=1)
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
        
        # HTML AMB DISSENY MILLORAT I BANDERES REALS
        html_content = """
        <!DOCTYPE html>
        <html lang="ca">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Futbol TV</title>
            <style>
                body { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; }
                h1 { text-align: center; color: #4caf50; font-size: 2.5em; margin-bottom: 30px; text-transform: uppercase; letter-spacing: 2px; }
                
                /* Targetes més amples per a TV */
                .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(450px, 1fr)); gap: 25px; }
                
                .card { 
                    background-color: #1e1e1e; 
                    border-radius: 15px; 
                    padding: 20px; 
                    box-shadow: 0 8px 16px rgba(0,0,0,0.5); 
                    border: 1px solid #333;
                }
                
                .header { 
                    display: flex; align-items: center; margin-bottom: 20px; 
                    border-bottom: 2px solid #333; padding-bottom: 15px; 
                }
                
                .time { 
                    font-size: 1.5em; font-weight: bold; color: #121212; 
                    background: #4caf50; padding: 5px 15px; border-radius: 8px; 
                }
                
                .teams { font-size: 1.4em; font-weight: bold; margin-left: 15px; color: #ffffff; }
                
                .channels { display: flex; flex-wrap: wrap; gap: 15px; }
                
                .btn { 
                    display: flex; align-items: center; text-decoration: none; 
                    color: white; background-color: #2c2c2c; 
                    padding: 12px 20px; border-radius: 10px; 
                    font-size: 1.1em; transition: transform 0.2s, background 0.2s; 
                    border: 1px solid #444;
                }
                
                .btn:hover { background-color: #4caf50; color: black; transform: scale(1.05); border-color: #4caf50; }
                
                /* Estil per a les imatges de les banderes */
                .flag-img { width: 24px; height: 18px; margin-right: 10px; border-radius: 2px; object-fit: cover; }
                
                .footer { text-align: center; margin-top: 50px; color: #666; font-size: 0.9em; }
            </style>
        </head>
        <body>
            <h1>⚽ Partits en Directe</h1>
            <div class="grid">
        """

        if not matches:
            html_content += '<div style="text-align:center; width:100%; font-size:2em; color:#777;">No hi ha partits ara mateix 😴</div>'

        for match in matches:
            home = match.get('homeTeam', 'Home')
            away = match.get('awayTeam', 'Away')
            hora = arreglar_hora(match.get('time', '00:00'))
            
            html_content += f"""
            <div class="card">
                <div class="header">
                    <span class="time">{hora}</span>
                    <span class="teams">{home} vs {away}</span>
                </div>
                <div class="channels">
            """
            
            for channel in match.get('channels', []):
                name = channel.get('channel_name', 'Canal')
                url = channel.get('url', '#')
                code = channel.get('channel_code', 'xx').lower() # Codi de país en minúscules
                
                # TRUC: Fem servir una web que ens dona la foto de la bandera pel codi
                img_bandera = f"https://flagcdn.com/24x18/{code}.png"
                
                html_content += f"""
                    <a href="{url}" class="btn">
                        <img src="{img_bandera}" class="flag-img" onerror="this.style.display='none'"> 
                        {name}
                    </a>
                """
            
            html_content += """
                </div>
            </div>
            """

        html_content += f"""
            </div>
            <div class="footer">Última actualització: {datetime.now().strftime('%H:%M')}</div>
        </body>
        </html>
        """

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print("ÈXIT: Web generada amb disseny PRO.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()