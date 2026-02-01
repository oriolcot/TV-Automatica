import requests
from datetime import datetime, timedelta

# URL de l'API
API_URL = "https://api.cdn-live.tv/api/v1/events/sports/?user=cdnlivetv&plan=free"

def arreglar_hora(hora_str):
    try:
        data_hora = datetime.strptime(hora_str, "%H:%M")
        # SUMA 1 HORA
        nova_hora = data_hora + timedelta(hours=1)
        return nova_hora.strftime("%H:%M")
    except:
        return hora_str

def obtenir_nom_esport(clau_api):
    # Diccionari de traduccions
    noms = {
        "Soccer": "FUTBOL ⚽",
        "NBA": "BÀSQUET (NBA) 🏀",
        "NFL": "NFL 🏈",
        "NHL": "HOQUEI (NHL) 🏒",
        "MLB": "BEISBOL ⚾",
        "F1": "FÓRMULA 1 🏎️",
        "MotoGP": "MOTOGP 🏍️",
        "Tennis": "TENNIS 🎾"
    }
    return noms.get(clau_api, clau_api.upper())

def main():
    try:
        print("Descarregant dades...")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"}
        response = requests.get(API_URL, headers=headers, timeout=15)
        data = response.json()
        
        tots_esports = data.get("cdn-live-tv", {})
        
        # 1. PRE-PROCESSAMENT: Mirem quins esports tenen partits reals
        esports_actius = []
        for clau, partits in tots_esports.items():
            if isinstance(partits, list) and len(partits) > 0:
                esports_actius.append(clau)

        # INICI HTML (MODE CLAR)
        html_content = """
        <!DOCTYPE html>
        <html lang="ca">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Esports TV</title>
            <style>
                /* Estil Clar (Light Mode) */
                body { 
                    background-color: #f0f2f5; 
                    color: #1c1e21; 
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
                    margin: 0; 
                    padding: 0; 
                }

                /* Menú de Navegació Superior */
                .navbar {
                    background-color: #ffffff;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    padding: 15px;
                    position: sticky;
                    top: 0;
                    z-index: 1000;
                    display: flex;
                    justify-content: center;
                    gap: 15px;
                    flex-wrap: wrap;
                }

                .nav-btn {
                    text-decoration: none;
                    color: #444;
                    font-weight: bold;
                    padding: 8px 16px;
                    border-radius: 20px;
                    background-color: #e4e6eb;
                    transition: all 0.2s ease;
                    text-transform: uppercase;
                    font-size: 0.9em;
                }

                .nav-btn:hover, .nav-btn.active {
                    background-color: #007aff; /* Blau Apple */
                    color: white;
                }

                .container { padding: 20px; max-width: 1200px; margin: 0 auto; }

                /* Títols de Secció */
                .sport-section { scroll-margin-top: 80px; /* Perquè el menú no tapi el títol */ }
                
                .sport-title { 
                    margin-top: 40px; 
                    margin-bottom: 20px; 
                    font-size: 1.8em; 
                    color: #1c1e21; 
                    border-bottom: 3px solid #007aff; 
                    display: inline-block;
                    padding-bottom: 5px;
                    font-weight: 800;
                    text-transform: uppercase;
                }

                .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; }
                
                /* Targetes Blanques */
                .card { 
                    background-color: #ffffff; 
                    border-radius: 12px; 
                    padding: 20px; 
                    box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
                    border: 1px solid #e1e3e8;
                    transition: transform 0.2s;
                }
                
                .header { 
                    display: flex; align-items: center; margin-bottom: 15px; 
                    padding-bottom: 10px; border-bottom: 1px solid #eee;
                }
                
                .time { 
                    font-size: 1.2em; font-weight: bold; color: #007aff; 
                    background: #ebf5ff; padding: 4px 10px; border-radius: 6px; 
                }
                
                .teams { font-size: 1.2em; font-weight: bold; margin-left: 12px; color: #333; }
                
                .channels { display: flex; flex-wrap: wrap; gap: 10px; }
                
                .btn { 
                    display: flex; align-items: center; text-decoration: none; 
                    color: #333; background-color: #f7f8fa; 
                    padding: 10px 15px; border-radius: 8px; 
                    font-size: 1em; border: 1px solid #ddd;
                    font-weight: 500;
                }
                
                .btn:hover { 
                    background-color: #007aff; 
                    color: white; 
                    border-color: #007aff; 
                }
                
                .flag-img { width: 22px; height: 16px; margin-right: 8px; border-radius: 2px; object-fit: cover; border: 1px solid #eee;}
                
                .footer { text-align: center; margin-top: 60px; color: #888; font-size: 0.8em; padding-bottom: 20px;}
            </style>
        </head>
        <body>
            
            <div class="navbar">
        """
        
        # Generem els botons del menú
        if not esports_actius:
             html_content += '<span style="color:#666">Sense categories actives</span>'
        else:
            for esport in esports_actius:
                nom_maco = obtenir_nom_esport(esport)
                html_content += f'<a href="#{esport}" class="nav-btn">{nom_maco}</a>'

        html_content += """
            </div>
            <div class="container">
        """

        # 3. CONTINGUT DELS PARTITS
        if not esports_actius:
            html_content += '<div style="text-align:center; margin-top:100px; font-size:1.5em; color:#888;">No hi ha esports en directe ara mateix 😴</div>'

        for esport in esports_actius:
            llista_partits = tots_esports[esport]
            nom_maco = obtenir_nom_esport(esport)
            
            # id=esport permet que el botó del menú baixi fins aquí
            html_content += f'<div id="{esport}" class="sport-section">'
            html_content += f'<div class="sport-title">{nom_maco}</div>'
            html_content += '<div class="grid">'

            for match in llista_partits:
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
                    code = channel.get('channel_code', 'xx').lower()
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
            
            html_content += '</div></div>' # Tancar grid i section

        html_content += f"""
            </div> <div class="footer">
                Última actualització: {datetime.now().strftime('%H:%M')} <br>
                Categories trobades: {', '.join([obtenir_nom_esport(e) for e in esports_actius])}
            </div>
        </body>
        </html>
        """

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print("ÈXIT: Web Light Mode generada.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()