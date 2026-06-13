import sqlite3

DB_PATH = 'datapolis.db'

def calcular_e_salvar_notas():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Cria a coluna nota_geral de forma segura
    try:
        cursor.execute("ALTER TABLE municipios ADD COLUMN nota_geral REAL")
    except sqlite3.OperationalError:
        pass # Ignora se a coluna já existir

    cursor.execute("SELECT codigo_ibge, populacao, ideb_anos_iniciais, cobertura_aps, ocorrencias_criminais, bolsa_familia_beneficiarios, despesa_educacao_pct FROM municipios")
    municipios = cursor.fetchall()

    # 2. Separa as matrizes para encontrar o Mínimo e Máximo (ignora nulos)
    vals_edu = [m['ideb_anos_iniciais'] for m in municipios if m['ideb_anos_iniciais'] is not None]
    vals_sau = [m['cobertura_aps'] for m in municipios if m['cobertura_aps'] is not None]
    vals_seg = [m['ocorrencias_criminais'] for m in municipios if m['ocorrencias_criminais'] is not None]
    vals_orc = [m['despesa_educacao_pct'] for m in municipios if m['despesa_educacao_pct'] is not None]
    
    vals_ass = []
    for m in municipios:
        if m['bolsa_familia_beneficiarios'] is not None and m['populacao']:
            vals_ass.append(m['bolsa_familia_beneficiarios'] / m['populacao'])

    # Extrai o piso e o teto do banco
    min_e, max_e = min(vals_edu), max(vals_edu)
    min_s, max_s = min(vals_sau), max(vals_sau)
    min_c, max_c = min(vals_seg), max(vals_seg)
    min_o, max_o = min(vals_orc), max(vals_orc)
    min_a, max_a = min(vals_ass), max(vals_ass)

    updates = []
    
    # 3. Calcula a Normalização de 0 a 1 para cada variável
    for m in municipios:
        nota = 0.0

        if m['ideb_anos_iniciais'] is not None:
            nota += (m['ideb_anos_iniciais'] - min_e) / (max_e - min_e)

        if m['cobertura_aps'] is not None:
            nota += (m['cobertura_aps'] - min_s) / (max_s - min_s)

        if m['ocorrencias_criminais'] is not None:
            # Fórmula invertida: crimes menores geram nota maior
            nota += (max_c - m['ocorrencias_criminais']) / (max_c - min_c)

        if m['despesa_educacao_pct'] is not None:
            nota += (m['despesa_educacao_pct'] - min_o) / (max_o - min_o)

        if m['bolsa_familia_beneficiarios'] is not None and m['populacao']:
            bf_pc = m['bolsa_familia_beneficiarios'] / m['populacao']
            nota += (bf_pc - min_a) / (max_a - min_a)

        updates.append((round(nota, 2), m['codigo_ibge']))

    # 4. Injeta as notas de 0 a 5 no banco de dados
    cursor.executemany("UPDATE municipios SET nota_geral = ? WHERE codigo_ibge = ?", updates)
    conn.commit()
    conn.close()

    print("Cálculo de normalização concluído! Notas de 0 a 5 gravadas no banco de dados.")

if __name__ == '__main__':
    calcular_e_salvar_notas()
