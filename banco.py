import sqlite3
import random

DB_PATH = 'datapolis.db'

def gerar_mock_brasil_inteiro():
    print("Iniciando geração de dados mockados para o Datapólis...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Puxamos a população para calcular dados proporcionais
    cursor.execute("SELECT codigo_ibge, populacao FROM municipios")
    municipios = cursor.fetchall()
    
    updates = []
    
    for codigo_ibge, populacao in municipios:
        # 1. EDUCAÇÃO
        ideb = round(random.uniform(3.8, 7.5), 1)
        ideb_delta = round(random.uniform(-0.5, 1.2), 1)
        
        # 2. SAÚDE
        aps = round(random.uniform(45.0, 100.0), 1)
        mort = round(random.uniform(5.0, 22.0), 1)
        mort_delta = round(random.uniform(-4.0, 2.0), 1)
        
        # 3. SEGURANÇA
        crimes = random.randint(80, 1200)
        crimes_delta = random.randint(-200, 150)
        
        # 4. ASSISTÊNCIA SOCIAL (Bolsa Família proporcional à população: 10% a 35%)
        pop = populacao if populacao else 10000
        bf = int(pop * random.uniform(0.10, 0.35))
        bf_delta = round(random.uniform(-3.0, 3.0), 1)
        
        # 5. ORÇAMENTO (A soma deve ser sempre 100%)
        edu = round(random.uniform(20.0, 35.0), 1)
        sau = round(random.uniform(15.0, 30.0), 1)
        adm = round(random.uniform(5.0, 12.0), 1)
        seg = round(random.uniform(1.0, 6.0), 1)
        inf = round(random.uniform(5.0, 15.0), 1)
        
        # O resto vai para "Outros"
        soma_parcial = edu + sau + adm + seg + inf
        outros = round(100.0 - soma_parcial, 1)
        if outros < 0: outros = 0.0
        
        # Adiciona na lista de processamento em lote
        updates.append((
            ideb, ideb_delta, 
            aps, mort, mort_delta, 
            crimes, crimes_delta, 
            bf, bf_delta,
            edu, sau, adm, seg, inf, outros,
            codigo_ibge
        ))

    # Atualiza o banco de dados de uma vez só (extremamente rápido)
    sql = '''
        UPDATE municipios SET 
            ideb_anos_iniciais=?, ideb_delta=?, 
            cobertura_aps=?, mortalidade_infantil=?, mortalidade_delta=?, 
            ocorrencias_criminais=?, ocorrencias_delta=?, 
            bolsa_familia_beneficiarios=?, bolsa_familia_delta=?,
            despesa_educacao_pct=?, despesa_saude_pct=?, despesa_administracao_pct=?, 
            despesa_seguranca_pct=?, despesa_infraestrutura_pct=?, despesa_outros_pct=?
        WHERE codigo_ibge=?
    '''
    
    print("Injetando dados no banco de dados...")
    cursor.executemany(sql, updates)
    conn.commit()
    conn.close()
    
    print(f"✅ Sucesso! {len(municipios)} municípios preenchidos com dados de teste realistas.")

if __name__ == '__main__':
    gerar_mock_brasil_inteiro()
