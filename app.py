"""
Datapólis — Backend Flask
=========================
Rotas:
  GET  /                              → index.html
  GET  /municipio/<codigo_ibge>       → municipio.html
  GET  /comparar/<cod1>               → selecionar_comparacao.html
  GET  /comparar/<cod1>/<cod2>        → comparacao.html
  GET  /api/search?q=<texto>          → autocomplete JSON
  GET  /api/notas-mapa                → notas 0-5 por município e estado (D3.js)
"""

import sqlite3
import os
from flask import Flask, render_template, jsonify, request, abort, session, redirect, url_for

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "datapolis.db")
app.secret_key = 'sua_chave_secreta_super_segura_aqui'

# ── Conexão ───────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Helpers ───────────────────────────────────────────────────────────────────

def calcular_nota_municipio(row) -> float | None:
    """
    Nota geral 0–5 calculada a partir dos indicadores do município.

    Pesos:
      PIB per Capita           → normaliza para 0–5   | 20 %
      IDEB (0–10)              → normaliza para 0–5   | 20 %
      Cobertura APS (0–100 %)  → normaliza para 0–5   | 15 %
      Mortalidade infantil     → inverso, 0–5          | 15 %
      Ocorrências / 100 mil    → inverso, 0–5          | 15 %
      Gasto com Saúde (%)      → normaliza para 0–5   | 15 %
    """
    pontos, pesos = [], []

    if row["pib_per_capita"] is not None:
        pontos.append(min(float(row["pib_per_capita"]) / 60000, 1) * 5)
        pesos.append(0.20)

    if row["ideb_anos_iniciais"] is not None and float(row["ideb_anos_iniciais"]) > 0:
        pontos.append((float(row["ideb_anos_iniciais"]) / 10) * 5)
        pesos.append(0.20)

    if row["cobertura_aps"] is not None and float(row["cobertura_aps"]) > 0:
        pontos.append((float(row["cobertura_aps"]) / 100) * 5)
        pesos.append(0.15)

    if row["mortalidade_infantil"] is not None:
        inv = max(0, 60 - float(row["mortalidade_infantil"])) / 60
        pontos.append(inv * 5)
        pesos.append(0.15)

    if row["ocorrencias_criminais"] is not None:
        inv = max(0, 5000 - float(row["ocorrencias_criminais"])) / 5000
        pontos.append(inv * 5)
        pesos.append(0.15)

    if row["despesa_saude_pct"] is not None:
        pontos.append(min(float(row["despesa_saude_pct"]) / 30, 1) * 5)
        pesos.append(0.15)

    if not pontos:
        return None

    total_peso = sum(pesos)
    return round(sum(p * w for p, w in zip(pontos, pesos)) / total_peso, 2)


def municipio_para_dict(row) -> dict:
    """
    Converte sqlite3.Row → dict pronto para o Jinja.

    Deltas ficam como float (Jinja compara > 0 / < 0).
    Campos de exibição decimal viram string (filtro | replace('.', ',')).
    Campos inteiros (populacao, bolsa, ocorrencias) ficam como int/float.
    """
    d = dict(row)

    # Deltas: sempre float para comparações no Jinja
    for delta in ["ideb_delta", "mortalidade_delta", "ocorrencias_delta"]:
        val = d.get(delta)
        d[delta] = 0.0 if val is None else float(val)

    # Campos decimais de exibição: string para | replace('.', ',')
    for campo in [
        "ideb_anos_iniciais",
        "cobertura_aps",
        "mortalidade_infantil",
        "despesa_educacao_pct", "despesa_saude_pct",
        "despesa_administracao_pct", "despesa_seguranca_pct",
        "despesa_infraestrutura_pct", "despesa_outros_pct"
    ]:
        if d.get(campo) is not None:
            d[campo] = str(d[campo])

    return d


def media_lista(lista: list, campo: str, como_int=False):
    """
    Média de um campo numa lista de dicts (ignora None).
    como_int=True  → retorna int  (para {:,} no template, ex: bolsa_familia)
    como_int=False → retorna str  (para | replace('.', ','))
    """
    valores = [float(m[campo]) for m in lista if m.get(campo) is not None]
    if not valores:
        return None
    media = round(sum(valores) / len(valores), 1)
    return int(media) if como_int else str(media)


# ── Rotas ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/municipio/<int:codigo_ibge>")
def municipio(codigo_ibge):
    conn = get_db()
    session['ultimo_municipio'] = codigo_ibge
    row = conn.execute(
        "SELECT * FROM municipios WHERE codigo_ibge = ?", (codigo_ibge,)
    ).fetchone()

    if row is None:
        conn.close()
        abort(404)

    dados = municipio_para_dict(row)
    populacao = row["populacao"]

    # 5 municípios com população mais próxima (excluindo o próprio)
    rows_sim = conn.execute("""
        SELECT * FROM municipios
        WHERE codigo_ibge != ?
        ORDER BY ABS(populacao - ?) ASC
        LIMIT 5
    """, (codigo_ibge, populacao)).fetchall()

    conn.close()

    similares = [municipio_para_dict(r) for r in rows_sim]

    media_similares = {
        "ideb":        media_lista(similares, "ideb_anos_iniciais"),          # str
        "aps":         media_lista(similares, "cobertura_aps"),                # str
        "mort":        media_lista(similares, "mortalidade_infantil"),         # str
        "ocorrencias": media_lista(similares, "ocorrencias_criminais"),        # str
        "bolsa":       media_lista(similares, "bolsa_familia_beneficiarios", como_int=True),  # int
        "pib":         media_lista(similares, "pib_per_capita"),               # str
        "edu":         media_lista(similares, "despesa_educacao_pct"),         # str
        "sau":         media_lista(similares, "despesa_saude_pct"),            # str
    }

    return render_template(
        "municipio.html",
        dados=dados,
        similares=similares,
        media_similares=media_similares,
    )


@app.route("/comparar/<int:cod1>")
def selecionar_comparacao(cod1):
    conn = get_db()
    cidade1 = conn.execute(
        "SELECT codigo_ibge, nome, uf FROM municipios WHERE codigo_ibge = ?",
        (cod1,)
    ).fetchone()
    conn.close()

    if cidade1 is None:
        abort(404)

    return render_template("selecionar_comparacao.html", cidade1=cidade1)


@app.route("/comparar/<int:cod1>/<int:cod2>")
def comparacao(cod1, cod2):
    conn = get_db()
    row1 = conn.execute(
        "SELECT * FROM municipios WHERE codigo_ibge = ?", (cod1,)
    ).fetchone()
    row2 = conn.execute(
        "SELECT * FROM municipios WHERE codigo_ibge = ?", (cod2,)
    ).fetchone()
    conn.close()

    if row1 is None or row2 is None:
        abort(404)

    return render_template("comparacao.html", c1=dict(row1), c2=dict(row2))

@app.route('/indicadores')
def ultimo_indicador():
    # Pega o último município da sessão. 
    # Se não existir (usuário acabou de abrir o site), usa 3106200 (Belo Horizonte) como fallback
    codigo = session.get('ultimo_municipio') or 3106200
    
    # Redireciona para a página do município correto
    return redirect(url_for('municipio', codigo_ibge=codigo))


# ── APIs ──────────────────────────────────────────────────────────────────────

@app.route("/api/search")
def api_search():
    """Autocomplete: retorna até 10 municípios cujo nome contenha o texto."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])

    conn = get_db()
    rows = conn.execute("""
        SELECT codigo_ibge, nome, uf
        FROM municipios
        WHERE nome LIKE ?
        ORDER BY nome ASC
        LIMIT 10
    """, (f"%{q}%",)).fetchall()
    conn.close()

    return jsonify([dict(r) for r in rows])


@app.route("/api/notas-mapa")
def api_notas_mapa():
    """
    Notas 0–5 para todos os municípios e médias por estado.
    Consumido pelo mapa.js para colorir o D3.
    """
    conn = get_db()
    rows = conn.execute("SELECT * FROM municipios").fetchall()
    conn.close()

    notas_municipios = {}
    acumulado_estados = {}

    for row in rows:
        nota = calcular_nota_municipio(row)
        if nota is None:
            continue
        cod = str(row["codigo_ibge"])
        uf  = row["uf"]
        notas_municipios[cod] = nota
        acumulado_estados.setdefault(uf, []).append(nota)

    notas_estados = {
        uf: round(sum(lst) / len(lst), 2)
        for uf, lst in acumulado_estados.items()
    }

    return jsonify({"municipios": notas_municipios, "estados": notas_estados})


# ── Erro 404 ──────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def nao_encontrado(e):
    return "<h2>404 — Município não encontrado</h2><a href='/'>Voltar</a>", 404


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)