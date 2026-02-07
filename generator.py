import requests
import json
import os
import sys
import base64
from datetime import datetime

# --- CONFIGURACIÓ ---
API_URL_CDN = os.environ.get("API_URL")
API_URL_PPV = os.environ.get("API_URL_PPV")
MEMORY_FILE = "memoria_partits.json"

# --- PLANTILLA HTML ---
INTERNAL_TEMPLATE = """<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Futbol & Esports</title>
<style>
:root { --bg: #0f172a; --card: #1e293b; --text: #e2e8f0; --accent: #3b82f6; --live: #ef4444; }
body { background: var(--bg); color: var(--text); font-family: sans-serif; margin: 0; padding: 20px; }
.navbar { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 15px; }
.nav-btn { background: var(--card); color: var(--text); padding: 8px 16px; border-radius: 20px; text-decoration: none; border: 1px solid #334155; white-space: nowrap; }
.sport-title { font-size: 1.5rem; font-weight: bold; margin: 30px 0 15px 0; border-left: 4px solid var(--accent); padding-left: 10px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
.card { background: var(--card); border-radius: 12px; overflow: hidden; border: 1px solid #334155; padding: 10px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;}
.channels { display: flex; flex-wrap: wrap; gap: 8px; }
.btn { background: #334155; padding: 6px 12px; border-radius: 6px; font-size: 0.85rem; cursor: pointer; color: white; display: flex; align-items: center; gap: 5px;}
.footer { margin-top: 40px; text-align: center; color: #64748b; border-top: 1px solid #334155; padding-top: 20px; }
</style>
</head>
<body>
<div class="navbar"></div>
<div id="content"></div>
<div class="footer">Actualitzat: </div>
<script>
function openLink(el) { try { window.open(atob(el.getAttribute('data-link')), '_blank'); } catch(e){} }
document.querySelectorAll('.utc-time').forEach(el => {
    el.innerText = new Date(el.getAttribute('data-ts').replace(' ', 'T')+'Z').toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
});
</script>
</body>
</html>"""

def log(msg):
    # Imprimim els logs per ERROR STANDARD (stderr) perquè no es barregin amb l'HTML
    sys.stderr.write(f"[LOG] {msg}\n")

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {}

def main():
    try:
        # Forcem codificació UTF-8 per la consola
        sys.stdout.reconfigure(encoding='utf-8')
        
        log("Iniciant generació...")
        memory = load_memory()
        
        # Filtrar partits (últimes 5 hores o futurs)
        matches = []
        now = datetime.utcnow()
        
        for m in memory.values():
            try:
                s_dt = datetime.strptime(m.get('start'), "%Y-%m-%d %H:%M")
                if (now - s_dt).total_seconds() < 5 * 3600:
                    matches.append(m)
            except: pass

        log(f"Partits vàlids trobats: {len(matches)}")

        # --- PARTIT DE DEBUG SI NO HI HA RES ---
        if not matches:
            log("⚠️ No hi ha partits reals. Afegint DEBUG MATCH.")
            matches.append({
                "custom_sport_cat": "DEBUG",
                "homeTeam": "TEST", "awayTeam": "SYSTEM",
                "start": now.strftime("%Y-%m-%d %H:%M"),
                "status": "live",
                "channels": [{"channel_name": "Check", "url": "https://google.com", "channel_code": "us"}]
            })

        # Generar contingut
        events_by_cat = {}
        for m in matches:
            cat = m.get('custom_sport_cat', 'Other')
            if cat not in events_by_cat: events_by_cat[cat] = []
            events_by_cat[cat].append(m)

        navbar_html = ""
        content_html = ""

        for sport in sorted(events_by_cat.keys()):
            navbar_html += f'<a href="#{sport}" class="nav-btn">{sport}</a>'
            content_html += f'<div id="{sport}"><div class="sport-title">{sport}</div><div class="grid">'
            
            for m in events_by_cat[sport]:
                utc = m.get('start')
                live = '<span style="color:#ef4444;font-weight:bold">LIVE</span>' if m.get('status') == 'live' else ''
                
                btns_html = ""
                for ch in m.get('channels', []):
                    try: link = base64.b64encode(ch.get('url').encode()).decode()
                    except: link = ""
                    btns_html += f'<div class="btn" data-link="{link}" onclick="openLink(this)">📺 {ch.get("channel_name")}</div>'

                content_html += f"""
                <div class="card">
                    <div class="header">
                        <span class="utc-time" data-ts="{utc}">{utc}</span> {live}
                        <strong>{m['homeTeam']} vs {m['awayTeam']}</strong>
                    </div>
                    <div class="channels">{btns_html}</div>
                </div>"""
            content_html += "</div></div>"

        # INSERCIÓ I IMPRESSIÓ FINAL
        final_html = INTERNAL_TEMPLATE.replace('', navbar_html)
        final_html = final_html.replace('', content_html)
        final_html = final_html.replace('', datetime.now().strftime("%d/%m %H:%M UTC"))

        # AQUÍ ESTÀ LA MÀGIA: IMPRIMIM L'HTML A LA CONSOLA
        print(final_html)
        log("HTML imprès a STDOUT correctament.")

    except Exception as e:
        log(f"CRITICAL ERROR: {e}")
        # En cas d'error, imprimim un HTML d'error visible
        print(f"<html><body><h1>ERROR GENERANT WEB</h1><p>{e}</p></body></html>")

if __name__ == "__main__":
    main()