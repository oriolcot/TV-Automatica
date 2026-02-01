import requests
import json
import os
from datetime import datetime, timedelta

# URL de l'API
API_URL = "https://api.cdn-live.tv/api/v1/events/sports/?user=cdnlivetv&plan=free"
FITXER_MEMORIA = "memoria_partits.json"

def obtenir_nom_esport(clau_api):
    noms = {
        "Soccer": "FUTBOL ⚽", "NBA": "BÀSQUET (NBA) 🏀", "NFL": "NFL 🏈",
        "NHL": "HOQUEI (NHL) 🏒", "MLB": "BEISBOL ⚾", "F1": "FÓRMULA 1 🏎️",
        "MotoGP": "MOTOGP 🏍️", "Tennis": "TENNIS 🎾", "Boxing": "BOXA 🥊",
        "Rugby": "RUGBI 🏉"
    }
    return noms.get(clau_api, clau_api.upper())

def arreglar_hora(hora_str):
    try:
        data_hora = datetime.strptime(hora_str, "%H:%M")
        nova_hora = data_hora + timedelta(hours=1) # Ajusta segons la teva zona
        return nova_hora.strftime("%H:%M")
    except:
        return hora_str

def carregar_memoria():
    if os.path.exists(FITXER_MEMORIA):
        try:
            with open(FITXER_MEMORIA, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def guardar_memoria(dades):
    with open(FITXER_MEMORIA, 'w', encoding='utf-8') as f:
        json.dump(dades, f, indent=4)

def netejar_esdeveniments_antics(diccionari_events):
    """
    Elimina partits que ja han acabat segur o fa massa hores que duren.
    Retorna el diccionari netejat.
    """
    events_actualitzats = {}
    ara = datetime.utcnow()

    for game_id, match in diccionari_events.items():
        # 1. Si l'estat és 'finished', fora.
        if match.get('status', '').lower() == 'finished':
            continue

        # 2. Control de temps (Seguretat de 6 hores)
        start_str = match.get('start') # "2026-02-01 23:00"
        if start_str:
            try:
                start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
                diferencia = ara - start_dt
                
                # Si fa més de 6 hores (21600s) que ha començat, l'esborrem de la memòria
                if diferencia.total_seconds() > 6 * 3600:
                    continue
                
                # Si el partit és de fa 2 dies (error api), fora també
                if diferencia.total_seconds() < -24 * 3600:
                    continue

            except ValueError:
                pass # Si falla la data, el mantenim per si de cas
        
        events_actualitzats[game_id] = match
    
    return events_actualitzats

def main():
    try:
        print("1. Carregant memòria anterior...")
        memoria = carregar_memoria()
        
        print("2. Descarregant dades noves de l'API...")
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            response = requests.get(API_URL, headers=headers, timeout=15)
            data_api = response.json()
            tots_esports_api = data_api.get("cdn-live-tv", {})
        except:
            print("Error connectant API, farem servir només la memòria.")
            tots_esports_api = {}

        # 3. FUSIONAR DADES (API + Memòria)
        # Convertim l'estructura de l'API en una llista plana per processar
        # La clau única serà el 'gameID' que ve al JSON
        
        # A. Primer, actualitzem la memòria amb el que diu l'API (és el més fiable)
        for esport, llista in tots_esports_api.items():
            if not isinstance(llista, list): continue
            for match in llista:
                game_id = match.get('gameID')
                if game_id:
                    # Afegim el camp 'esport_categoria' per saber on pintar-lo després
                    match['custom_sport_cat'] = esport 
                    memoria[game_id] = match

        # B. Netegem la memòria (esborrem els antics)
        memoria_neta = netejar_esdeveniments_antics(memoria)
        
        # C. Guardem la nova memòria al disc
        guardar_memoria(memoria_neta)
        
        # 4. RECONSTRUIR L'ESTRUCTURA PER A L'HTML
        # Hem de tornar a agrupar per categories (Soccer, NBA...)
        events_per_html = {}
        for game_id, match in memoria_neta.items():
            cat = match.get('custom_sport_cat', 'Altres')
            if cat not in events_per_html:
                events_per_html[cat] = []
            events_per_html[cat].append(match)

        # Ordenar partits per hora dins de cada categoria
        for cat in events_per_html:
            events_per_html[cat].sort(key=lambda x: x.get('time', '00:00'))

        # Llista de categories actives per al menú
        esports_actius = list(events_per_html.keys())

        # -----------------------------------------------------------
        # GENERACIÓ HTML (Igual que abans)
        # -----------------------------------------------------------
        html_content = """
        <!DOCTYPE html>
        <html lang="ca">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Esports TV</title>
            <style>
                body { background-color: #f0f2f5; color: #1c1e21; font-family: -apple-system, sans-serif; margin: 0; padding: 0; }
                .navbar { background-color: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 15px; position: sticky; top: 0; z-index: 1000; display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; }
                .nav-btn { text-decoration: none; color: #444; font-weight: bold; padding: 8px 16px; border-radius: 20px; background-color: #e4e6eb; transition: all 0.2s; text-transform: uppercase; font-size: 0.85em; }
                .nav-btn:hover { background-color: #007aff; color: white; }
                .container { padding: 20px; max-width: 1200px; margin: 0 auto; }
                .sport-section { scroll-margin-top: 80px; }
                .sport-title { margin-top: 40px; margin-bottom: 20px; font-size: 1.8em; color: #1c1e21; border-bottom: 3px solid #007aff; display: inline-block; padding-bottom: 5px; font-weight: 800; text-transform: uppercase; }
                .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px; }
                .card { background-color: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e1e3e8; }
                .header { display: flex; align-items: center; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
                .time { font-size: 1.2em; font-weight: bold; color: #007aff; background: #ebf5ff; padding: 4px 10px; border-radius: 6px; }
                .teams { font-size: 1.1em; font-weight: bold; margin-left: 12px; color: #333; line-height: 1.2; }
                .channels { display: flex; flex-wrap: wrap; gap: 8px; }
                .btn { display: flex; align-items: center; text-decoration: none; color: #333; background-color: #f7f8fa; padding: 8px 12px; border-radius: 8px; font-size: 0.95em; border: 1px solid #ddd; font-weight: 500; }
                .btn:hover { background-color: #007aff; color: white; border-color: #007aff; }
                .flag-img { width: 20px; height: 15px; margin-right: 8px; border-radius: 2px; object-fit: cover; border: 1px solid #eee;}
                .footer { text-align: center; margin-top: 60px; color: #888; font-size: 0.8em; padding-bottom: 20px;}
            </style>
        </head>
        <body>
            <div class="navbar">
        """
        
        if not esports_actius:
             html_content += '<span style="color:#666">Sense partits en memòria</span>'
        else:
            for esport in esports_actius:
                nom_maco = obtenir_nom_esport(esport)
                html_content += f'<a href="#{esport}" class="nav-btn">{nom_maco}</a>'

        html_content += '</div><div class="container">'

        if not esports_actius:
            html_content += '<div style="text-align:center; margin-top:100px; font-size:1.5em; color:#888;">No hi ha esports actius 😴</div>'

        for esport in esports_actius:
            llista_partits = events_per_html[esport]
            nom_maco = obtenir_nom_esport(esport)
            
            html_content += f'<div id="{esport}" class="sport-section"><div class="sport-title">{nom_maco}</div><div class="grid">'

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
                    
                    html_content += f"""<a href="{url}" class="btn"><img src="{img_bandera}" class="flag-img" onerror="this.style.display='none'"> {name}</a>"""
                
                html_content += "</div></div>"
            
            html_content += '</div></div>'

        html_content += f"""
            </div>
            <div class="footer">
                Última actualització: {datetime.now().strftime('%H:%M')} <br>
                Mode Persistent Activat (6h) 💾
            </div>
        </body>
        </html>
        """

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print("ÈXIT: Web generada amb MEMÒRIA PERSISTENT.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()