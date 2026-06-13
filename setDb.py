import sqlite3
import requests

def criar_banco():
    conn = sqlite3.connect('datapolis.db')
    cursor = conn.cursor()

    # Criação da tabela baseada nas métricas do seu design
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS municipios (
        codigo_ibge INTEGER PRIMARY KEY,
        nome TEXT NOT NULL,
        uf TEXT NOT NULL,
        regiao TEXT NOT NULL,
        populacao INTEGER DEFAULT 0,
        capital BOOLEAN DEFAULT 0,
        
        -- Educação
        ideb_anos_iniciais REAL DEFAULT 0.0,
        ideb_delta REAL DEFAULT 0.0,
        
        -- Saúde
        cobertura_aps REAL DEFAULT 0.0,
        mortalidade_infantil REAL DEFAULT 0.0,
        mortalidade_delta REAL DEFAULT 0.0,
        
        -- Segurança
        ocorrencias_criminais INTEGER DEFAULT 0,
        ocorrencias_delta INTEGER DEFAULT 0,
        
        -- Assistência Social
        bolsa_familia_beneficiarios INTEGER DEFAULT 0,
        bolsa_familia_delta REAL DEFAULT 0.0,
        
        -- Orçamento (Despesas em %)
        despesa_educacao_pct REAL DEFAULT 0.0,
        despesa_saude_pct REAL DEFAULT 0.0,
        despesa_administracao_pct REAL DEFAULT 0.0,
        despesa_seguranca_pct REAL DEFAULT 0.0,
        despesa_infraestrutura_pct REAL DEFAULT 0.0,
        despesa_outros_pct REAL DEFAULT 0.0
    )
    ''')

    print("Buscando municípios na API do IBGE...")
    response = requests.get('https://servicodados.ibge.gov.br/api/v1/localidades/municipios')
    municipios_ibge = response.json()

    print(f"Inserindo {len(municipios_ibge)} municípios no banco com dados zerados...")
    
    for mun in municipios_ibge:
        codigo_ibge = mun['id']
        nome = mun['nome']
        
        # Bloco de segurança para lidar com entidades que vêm com microrregiao vazia (None)
        try:
            uf = mun['microrregiao']['mesorregiao']['UF']['sigla']
            regiao = mun['microrregiao']['mesorregiao']['UF']['regiao']['nome']
        except TypeError:
            # Caso a microrregião seja None, tenta buscar pela hierarquia nova (Região Imediata)
            try:
                uf = mun['regiao-imediata']['regiao-intermediaria']['UF']['sigla']
                regiao = mun['regiao-imediata']['regiao-intermediaria']['UF']['regiao']['nome']
            except (TypeError, KeyError):
                # Se falhar novamente (ex: Lagoas do RS), define como Não Disponível
                uf = "ND"
                regiao = "ND"
        
        cursor.execute('''
        INSERT OR IGNORE INTO municipios (codigo_ibge, nome, uf, regiao)
        VALUES (?, ?, ?, ?)
        ''', (codigo_ibge, nome, uf, regiao))

    conn.commit()
    conn.close()
    print("Banco de dados criado e populado com sucesso!")

if __name__ == '__main__':
    criar_banco()
