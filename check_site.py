import requests
import difflib
import os
import hashlib
import json
from slack_sdk import WebClient

# Configurações
URLS = [
    "https://olist.com/",
    "https://olist.com/planos/"
]

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_CANAL = "#monitoramento-site"

def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()

has_changes = False
changed_url = ""
diff_text = ""
intuitive_diff_lines = []
planos_html = ""

for url in URLS:
    print(f"✅ Verificando: {url}")
    resposta = requests.get(url)
    pagina_atual = resposta.text

    hash_nome = hash_url(url)
    arquivo_antigo = f"pagina_antiga_{hash_nome}.html"

    mudanca_detectada = False
    diff_texto = ""

    if os.path.exists(arquivo_antigo):
        with open(arquivo_antigo, "r", encoding="utf-8") as f:
            pagina_antiga = f.read()

        diff = list(difflib.unified_diff(
            pagina_antiga.splitlines(),
            pagina_atual.splitlines(),
            lineterm=""
        ))
        diff_texto = "\n".join(diff)

        # Processar diff "humano"
        i = 0
        while i < len(diff):
            line = diff[i]
            if line.startswith("- ") and i + 1 < len(diff) and diff[i + 1].startswith("+ "):
                intuitive_diff_lines.append(f"🔸 De: \"{line[2:].strip()}\"")
                intuitive_diff_lines.append(f"🔸 Para: \"{diff[i+1][2:].strip()}\"")
                i += 2
            elif line.startswith("- ") and not (i + 1 < len(diff) and diff[i + 1].startswith("+ ")):
                intuitive_diff_lines.append(f"🔸 Removido: \"{line[2:].strip()}\"")
                i += 1
            elif line.startswith("+ ") and not (i > 0 and diff[i - 1].startswith("- ")):
                intuitive_diff_lines.append(f"🔸 Adicionado: \"{line[2:].strip()}\"")
                i += 1
            else:
                i += 1

        if diff_texto.strip():
            mudanca_detectada = True
            print(f"⚠️ Mudança detectada em {url}!")
    else:
        print(f"Primeira execução para {url}, salvando versão inicial.")

    with open(arquivo_antigo, "w", encoding="utf-8") as f:
        f.write(pagina_atual)

    if mudanca_detectada:
        has_changes = True
        changed_url = url
        diff_text = diff_texto
        slack_client = WebClient(token=SLACK_TOKEN)
        slack_client.chat_postMessage(
            channel=SLACK_CANAL,
            text=(
                f":warning: *Mudança detectada!*\n"
                f"URL: {url}\n"
                f"Linhas modificadas: {len(diff_texto.splitlines())} linhas"
            )
        )

    # Se for a página de planos, capturar o HTML
    if url == "https://olist.com/planos/":
        planos_html = pagina_atual

# Salvar anexo da página de planos
with open("planos_atual.html", "w", encoding="utf-8") as f:
    f.write(planos_html)

# Preparar safe outputs
planos_html_safe = planos_html.replace("\n", " ").replace("'", '"')[:9000]
diff_text_safe = diff_text.replace("\n", " ").replace("'", '"')[:9000]
intuitive_diff_text = "\n".join(intuitive_diff_lines)[:9000]

# Exporta outputs para o GitHub Actions
with open(os.getenv('GITHUB_OUTPUT'), 'a') as fh:
    fh.write(f"has_changes={'true' if has_changes else 'false'}\n")
    fh.write(f"changed_url={changed_url}\n")
    fh.write(f"diff_text={diff_text_safe}\n")
    fh.write(f"intuitive_diff_text={intuitive_diff_text}\n")
    fh.write(f"planos_html={planos_html_safe}\n")
