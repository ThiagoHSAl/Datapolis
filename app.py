from flask import Flask, render_template, abort, request, jsonify
import sqlite3

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('datapolis.db')
    conn.row_factory = sqlite3.Row # Permite acessar as colunas pelo nome
    return conn

# Rota para a página inicial (Busca)
@app.route('/')
def index():
    return render_template('index.html')

# Rota dinâmica para o dashboard do município
@app.route('/municipio/<int:codigo_ibge>')
def municipio(codigo_ibge):
    conn = sqlite3.connect('datapolis.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Puxa a cidade principal
    cursor.execute("SELECT * FROM municipios WHERE codigo_ibge = ?", (codigo_ibge,))
    mun = cursor.fetchone()
    
    if not mun:
        conn.close()
        return "Município não encontrado", 404
        
    # 2. Busca os 5 municípios com população mais próxima (excluindo ele mesmo)
    cursor.execute("""
        SELECT * FROM municipios 
        WHERE codigo_ibge != ? AND populacao IS NOT NULL
        ORDER BY ABS(populacao - ?) LIMIT 5
    """, (codigo_ibge, mun['populacao']))
    similares = cursor.fetchall()
    conn.close()

    # 3. Calcula as médias do grupo de cidades similares
    soma = {'ideb': 0, 'aps': 0, 'mort': 0, 'ocorrencias': 0, 'bolsa': 0, 'edu': 0, 'sau': 0}
    count = {'ideb': 0, 'aps': 0, 'mort': 0, 'ocorrencias': 0, 'bolsa': 0, 'edu': 0, 'sau': 0}
    
    for s in similares:
        if s['ideb_anos_iniciais'] is not None: soma['ideb'] += s['ideb_anos_iniciais']; count['ideb'] += 1
        if s['cobertura_aps'] is not None: soma['aps'] += s['cobertura_aps']; count['aps'] += 1
        if s['mortalidade_infantil'] is not None: soma['mort'] += s['mortalidade_infantil']; count['mort'] += 1
        if s['ocorrencias_criminais'] is not None: soma['ocorrencias'] += s['ocorrencias_criminais']; count['ocorrencias'] += 1
        if s['bolsa_familia_beneficiarios'] is not None: soma['bolsa'] += s['bolsa_familia_beneficiarios']; count['bolsa'] += 1
        if s['despesa_educacao_pct'] is not None: soma['edu'] += s['despesa_educacao_pct']; count['edu'] += 1
        if s['despesa_saude_pct'] is not None: soma['sau'] += s['despesa_saude_pct']; count['sau'] += 1
        
    media_similares = {
        'ideb': round(soma['ideb'] / count['ideb'], 1) if count['ideb'] > 0 else None,
        'aps': round(soma['aps'] / count['aps'], 1) if count['aps'] > 0 else None,
        'mort': round(soma['mort'] / count['mort'], 1) if count['mort'] > 0 else None,
        'ocorrencias': int(soma['ocorrencias'] / count['ocorrencias']) if count['ocorrencias'] > 0 else None,
        'bolsa': int(soma['bolsa'] / count['bolsa']) if count['bolsa'] > 0 else None,
        'edu': round(soma['edu'] / count['edu'], 1) if count['edu'] > 0 else None,
        'sau': round(soma['sau'] / count['sau'], 1) if count['sau'] > 0 else None,
    }

    # Passamos as novas variáveis para o HTML
    return render_template('municipio.html', dados=mun, similares=similares, media_similares=media_similares)

# Nova rota para a busca em tempo real (autocomplete)
@app.route('/api/search')
def search():
    q = request.args.get('q', '').strip()
    if len(q) < 1:
        return jsonify([]) # Retorna lista vazia se não tiver texto
    
    conn = get_db_connection()
    # Busca municípios cujo nome contenha as letras digitadas (LIKE ignora maiúsculas/minúsculas no SQLite)
    # LIMIT 8 para não poluir a tela com muitos resultados
    query = "SELECT codigo_ibge, nome, uf FROM municipios WHERE nome LIKE ? LIMIT 8"
    resultados = conn.execute(query, ('%' + q + '%',)).fetchall()
    conn.close()
    
    # Transforma os resultados em uma lista de dicionários para o Javascript entender
    return jsonify([dict(r) for r in resultados])

@app.route('/comparar/<int:id1>')
def selecionar_comparacao(id1):
    conn = sqlite3.connect('datapolis.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM municipios WHERE codigo_ibge = ?", (id1,))
    cidade1 = cursor.fetchone()
    conn.close()
    
    if not cidade1:
        return "Município base não encontrado", 404
        
    return render_template('selecionar_comparacao.html', cidade1=cidade1)

@app.route('/comparar/<int:id1>/<int:id2>')
def comparacao(id1, id2):
    conn = sqlite3.connect('datapolis.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM municipios WHERE codigo_ibge = ?", (id1,))
    c1 = cursor.fetchone()
    cursor.execute("SELECT * FROM municipios WHERE codigo_ibge = ?", (id2,))
    c2 = cursor.fetchone()
    conn.close()
    
    if not c1 or not c2:
        return "Municípios não encontrados", 404
        
    return render_template('comparacao.html', c1=c1, c2=c2)

@app.route('/api/notas-mapa')
def notas_mapa():
    conn = sqlite3.connect('datapolis.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Dicionário com as notas dos municípios (0 a 5)
    cursor.execute("SELECT codigo_ibge, nota_geral FROM municipios WHERE nota_geral IS NOT NULL")
    mun_notas = {str(row['codigo_ibge']): row['nota_geral'] for row in cursor.fetchall()}

    # Dicionário com a média dos estados (0 a 5)
    cursor.execute("SELECT uf, AVG(nota_geral) as media FROM municipios WHERE nota_geral IS NOT NULL GROUP BY uf")
    est_notas = {row['uf']: round(row['media'], 2) for row in cursor.fetchall()}

    conn.close()
    return jsonify({"municipios": mun_notas, "estados": est_notas})

if __name__ == '__main__':
    app.run(debug=True)
