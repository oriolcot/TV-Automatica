import requests
import json
import os
import shutil
import base64
from datetime import datetime

# --- CONFIGURACIÓ ---
API_URL_CDN = os.environ.get("API_URL")
API_URL_PPV = os.environ.get("API_URL_PPV")
MEMORY_FILE = "memoria_partits.json"
BACKUP_FILE = "memoria_backup.json"

# --- PLANTILLA HTML INCORPORADA (NO DEPÈN DE CAP FITXER EXTERN) ---
INTERNAL_TEMPLATE = """<!DOCTYPE html>
<html lang="ca">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Futbol & Esports</title>
    <style>
        :root { --bg: #0f172a; --card: #1e293b; --text: #e2e8f0; --accent: #3b82f6; --live: #ef4444; }
        body { background: var(--bg); color: var(--text); font-family: system-ui, sans-serif; margin: 0; padding: 20px; }
        .navbar { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 15px; margin-bottom: 20px; scrollbar-width: none; }
        .nav-btn { background: var(--card); color: var(--text); padding: 8px 16px; border-radius: 20px; text-decoration: none; border: 1px solid #334155; white-space: nowrap; font-size: 0.9rem; }
        .nav-btn:hover { background: var(--accent); border-color: var(--accent); }
        .sport-title { font-size: 1.5rem; font-weight: bold; margin: 30px 0 15px 0; border-left: 4px solid var(--accent); padding-left: 10px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
        .card { background: var(--card); border-radius: 12px; overflow: hidden; border: 1px solid #334155; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
        .header { padding: 15px; background: rgba(0,0,0,0.2); display: flex; justify-content: space-between; align-items: center; }
        .time { font-family: monospace; color: #94a3b8; font-size: 0.9rem; }
        .live-badge { background: var(--live); color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; animation: pulse 2s infinite; }
        .teams { font-weight: 600; text-align: right; flex-grow: 1; margin-left: 10px; }
        .channels { padding: 10px; display: flex; flex-wrap: wrap; gap: 8px; }
        .btn { background: #334155; padding: 6px 12px; border-radius: 6px; font-size: 0.85rem; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: 0.2s; text-decoration: none; color: white; }
        .btn:hover { background: var(--accent); }
        .flag-img { width: 16px; height: 12px; object-fit: cover; border-radius: 2px; }
        .footer { margin-top: 40px; text-align: center; color: #64748b; font-size: 0.8rem; border-top: 1px solid #334155; padding-top: 20px; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
</head>
<body>
    <div class="navbar" id="navbar">
        </div>

    <div id="content">
        </div>

    <div class="footer">
        Última actualització: </div>

    <script>
        // Convertir hora UTC a local
        document.querySelectorAll('.time').forEach(el => {
            const utc = el.getAttribute('data-utc');
            if(utc) {
                const date = new Date(utc.replace(' ', 'T') + 'Z');
                el.textContent = date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            }
        });

        // Obrir enllaços base64
        function openLink(el) {
            const raw = el.getAttribute('data-link');
            if(raw) {
                try {
                    const url = atob(raw);
                    window.open(url, '_blank');
                } catch(e) { console.error("Error URL", e); }
            }
        }
    </script>
</body>
</html>"""

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {}

def get_sport_name(api_key):
    names = { 
        "Soccer": "FUTBOL ⚽", "NBA": "BÀSQUET (NBA) 🏀", "NFL": "NFL 🏈", 
        "NHL": "HOQUEI (NHL) 🏒", "MLB": "BEISBOL ⚾", "F1": "FÓRMULA 1 🏎️", 
        "MotoGP": "MOTOGP 🏍️", "Tennis": "TENNIS 🎾", "Boxing": "BOXA 🥊", "Rugby": "RUGBI 🏉" 
    }
    return names.get(api_key, api_key.upper())

def main():
    try:
        # 1. CARREGAR DADES (Ja sabem que això funciona perquè el JSON està ple)
        print("📂 Llegint memòria de partits...")
        memory = load_memory()
        
        if not memory:
            print("⚠️ ALERTA: La memòria està buida! Assegura't que l'API està funcionant.")
            # Si la memòria està buida, intentem fer servir el backup per no deixar la web en blanc
            if os.path.exists(BACKUP_FILE):
                with open(BACKUP_FILE, 'r') as f: memory = json.load(f)

        print(f"✅ Partits carregats: {len(memory)}")

        # 2. FILTRAR I ORDENAR
        # Només volem partits futurs o recents (últimes 4 hores)
        final_mem = {}
        now = datetime.utcnow()
        for gid, m in memory.items():
            try:
                s_dt = datetime.strptime(m.get('start'), "%Y-%m-%d %H:%M")
                # Si el partit és de fa menys de 5 hores o és futur
                if (now - s_dt).total_seconds() < 5 * 3600:
                    final_mem[gid] = m
            except: pass
        
        # 3. GENERAR HTML
        events_by_cat = {}
        for m in final_mem.values():
            cat = m.get('custom_sport_cat', 'Other')
            if cat not in events_by_cat: events_by_cat[cat] = []
            m['channels'].sort(key=lambda x: 10 if x.get('channel_code') in ['es','mx'] else 1, reverse=True)
            events_by_cat[cat].append(m)

        active_sports = sorted(list(events_by_cat.keys()))
        navbar = ""
        content = ""
        
        if not active_sports:
            content = "<div style='text-align:center; padding:50px; color:#94a3b8;'>😴 No hi ha partits en viu ara mateix.</div>"
        
        for sport in active_sports:
            nice = get_sport_name(sport)
            navbar += f'<a href="#{sport}" class="nav-btn">{nice}</a>'
            
            # Ordenar per hora
            matches = sorted(events_by_cat[sport], key=lambda x: x.get('start'))
            
            content += f'<div id="{sport}" class="sport-section"><div class="sport-title">{nice}</div><div class="grid">'
            
            for m in matches:
                utc = m.get('start', '')
                is_live = m.get('status', '').lower() == 'live'
                badges = '<span class="live-badge">LIVE</span> ' if is_live else ''
                
                content += f"""
                <div class="card">
                    <div class="header">
                        <span class="time" data-utc="{utc}">--:--</span>
                        {badges}
                        <span class="teams">{m['homeTeam']} vs {m['awayTeam']}</span>
                    </div>
                    <div class="channels">
                """
                
                for ch in m['channels']:
                    name = ch.get('channel_name', 'Link')
                    url = ch.get('url', '#')
                    code = ch.get('channel_code', 'xx').lower()
                    img = "https://fav.farm/📺" if code == 'ppv' else f"https://flagcdn.com/24x18/{code}.png"
                    
                    try: enc_url = base64.b64encode(url.encode('utf-8')).decode('utf-8')
                    except: enc_url = ""
                    
                    content += f"""
                    <div class="btn" style="cursor:pointer;" data-link="{enc_url}" onclick="openLink(this)">
                        <img src="{img}" class="flag-img" onerror="this.style.display='none'"> {name}
                    </div>
                    """
                content += "</div></div>"
            content += "</div></div>"

        # 4. INSERIR A LA PLANTILLA INTERNA
        print("🎨 Generant HTML...")
        html = INTERNAL_TEMPLATE.replace('', navbar)
        html = html.replace('', content)
        html = html.replace('', datetime.now().strftime("%d/%m/%Y %H:%M UTC"))
        
        # 5. GUARDAR FITXER
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        print(f"✅ index.html generat amb èxit! Mida: {len(html)} bytes")

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()