import requests
import json
import os
import sys
import base64
from datetime import datetime

MEMORY_FILE = "memoria_partits.json"

# --- PLANTILLA MÍNIMA PER NO FALLAR ---
INTERNAL_TEMPLATE = """<!DOCTYPE html>
<html lang="ca">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DEBUG MODE</title>
<style>
body { background: #111; color: #eee; font-family: monospace; padding: 20px; }
.card { border: 1px solid #444; padding: 10px; margin: 10px 0; background: #222; }
.live { color: red; font-weight: bold; }
h1 { color: #3b82f6; }
</style>
</head>
<body>
<h1>MODE DIAGNÒSTIC</h1>
<p>Si veus això, el Python ha funcionat.</p>
<hr>
</body>
</html>"""

def main():
    try:
        # Configurem la sortida per UTF-8 per evitar errors amb emojis
        sys.stdout.reconfigure(encoding='utf-8')
        
        # 1. Carreguem memòria (sense API per ara, només volem veure el que tenim)
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                memory = json.load(f)
        else:
            print("<h1>❌ ERROR: No trobo memoria_partits.json</h1>")
            return

        # 2. NO FILTREM RES (Agafem tot el que hi ha al JSON)
        matches = list(memory.values())
        print(f"<p>Partits totals al JSON: {len(matches)}</p>")

        # 3. Generem HTML bàsic
        html_matches = ""
        for m in matches:
            titol = f"{m.get('homeTeam')} vs {m.get('awayTeam')}"
            hora = m.get('start')
            html_matches += f"<div class='card'>[{hora}] <strong>{titol}</strong></div>"

        if not html_matches:
            html_matches = "<h2>⚠️ El JSON existeix però està buit (0 partits).</h2>"

        # 4. Imprimim
        final_html = INTERNAL_TEMPLATE.replace('', html_matches)
        print(final_html)

    except Exception as e:
        # Si peta, això sortirà a la web gràcies al canvi del YML
        print(f"<h1>💥 CRITICAL PYTHON CRASH</h1>")
        print(f"<pre>{str(e)}</pre>")

if __name__ == "__main__":
    main()