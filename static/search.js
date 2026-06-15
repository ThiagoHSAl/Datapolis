// static/search.js

// Função modularizada para lidar com a busca em qualquer input
function initAutocomplete(inputId, dropdownId) {
    const searchInput = document.getElementById(inputId);
    const dropdown = document.getElementById(dropdownId);
  
    if (!searchInput || !dropdown) return; // Se o elemento não existir na página, aborta silenciosamente.
  
    searchInput.addEventListener('input', async function() {
      const query = this.value.trim();
      
      // Se apagar o texto, esconde a janela
      if (query.length === 0) {
        dropdown.classList.remove('active');
        dropdown.innerHTML = '';
        return;
      }
  
      try {
        // Busca na rota da API criada no Flask
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const municipios = await response.json();
        
        dropdown.innerHTML = '';
  
        if (municipios.length > 0) {
          // Renderiza os resultados retornados do banco de dados
          const baseUrl = window.URL_BASE_BUSCA || '/municipio/';
          dropdown.innerHTML = municipios.map(m => `
            <div class="autocomplete-item nav-dropdown-item" onclick="window.location.href='${baseUrl}${m.codigo_ibge}'">
              <span class="autocomplete-name nav-name">${m.nome_municipio}</span>
              <span class="autocomplete-uf nav-uf">${m.uf}</span>
            </div>
          `).join('');
        } else {
          // Caso a busca não retorne nada
          dropdown.innerHTML = `
            <div class="autocomplete-item nav-dropdown-item" style="cursor: default; background: transparent;">
              <span class="autocomplete-name nav-name" style="color: var(--mid); font-weight: 400;">Nenhum município encontrado.</span>
            </div>`;
        }
        
        dropdown.classList.add('active');
  
      } catch (error) {
        console.error("Erro na busca:", error);
      }
    });
  
    // Esconde a janela de busca se o usuário clicar fora dela
    document.addEventListener('click', function(e) {
      if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.remove('active');
      }
    });
  }
  
  // Quando a página carregar, ele tenta inicializar as buscas
  document.addEventListener('DOMContentLoaded', () => {
      // Inicializa a busca principal (da tela inicial index.html)
      initAutocomplete('mainSearch', 'autocompleteDropdown');
      
      // Inicializa a busca da navbar (para as páginas que possuem a navbar com busca)
      initAutocomplete('navSearchInput', 'navDropdown');
  });
  
