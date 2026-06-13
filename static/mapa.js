document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById('map-container');
    if (!container) return;
  
    container.innerHTML = '';
    const width = container.clientWidth;
    const height = 600;
  
    const svg = d3.select("#map-container")
      .append("svg")
      .attr("width", "100%")
      .attr("height", "100%")
      .attr("viewBox", `0 0 ${width} ${height}`)
      .style("background", "#eef2f5"); 
  
    const g = svg.append("g");
    const gEstados = g.append("g");
    const gMunicipios = g.append("g"); 
  
    const zoom = d3.zoom()
      .scaleExtent([1, 15])
      .on("zoom", (event) => { g.attr("transform", event.transform); });
    svg.call(zoom);
  
    const tooltip = d3.select("#map-tooltip");
  
    const btnVoltar = d3.select("#map-container")
      .append("button")
      .text("← Voltar para o Brasil")
      .style("position", "absolute")
      .style("top", "20px")
      .style("left", "20px")
      .style("padding", "0.6rem 1rem")
      .style("background", "var(--ink)")
      .style("color", "var(--paper)")
      .style("border", "none")
      .style("border-radius", "4px")
      .style("cursor", "pointer")
      .style("font-family", "'Syne', sans-serif")
      .style("font-weight", "700")
      .style("display", "none")
      .style("box-shadow", "0 4px 12px rgba(0,0,0,0.15)");
  
    const projection = d3.geoMercator();
    const path = d3.geoPath().projection(projection);
    let estadoAtivo = null;
  
    const siglaParaCodigo = {
        'AC': '12', 'AL': '27', 'AP': '16', 'AM': '13', 'BA': '29', 'CE': '23', 'DF': '53', 
        'ES': '32', 'GO': '52', 'MA': '21', 'MT': '51', 'MS': '50', 'MG': '31', 'PA': '15', 
        'PB': '25', 'PR': '41', 'PE': '26', 'PI': '22', 'RJ': '33', 'RN': '24', 'RS': '43', 
        'RO': '11', 'RR': '14', 'SC': '42', 'SP': '35', 'SE': '28', 'TO': '17'
    };
  
    // ==========================================
    // NOVA LÓGICA: CARREGA MAPA E NOTAS JUNTOS
    // ==========================================
    Promise.all([
        d3.json("https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"),
        fetch('/api/notas-mapa').then(res => res.json())
    ]).then(([dataEstados, notasData]) => {
  
        // Escala Escalar de Cores: 0 (Vermelho) -> 2.5 (Cinza neutro) -> 5 (Verde)
        const colorScale = d3.scaleLinear()
            .domain([0, 2.5, 5])
            .range(["#d4500a", "#d8d2c4", "#388e3c"]);
  
        projection.fitSize([width, height], dataEstados);
  
        // ==========================
        // 1. DESENHAR OS ESTADOS
        // ==========================
        gEstados.selectAll("path")
            .data(dataEstados.features)
            .enter()
            .append("path")
            .attr("d", path)
            .style("fill", d => {
                const nota = notasData.estados[d.properties.sigla];
                return nota ? colorScale(nota) : "var(--accent)"; // fallback se não tiver nota
            }) 
            .style("stroke", "#ffffff")
            .style("stroke-width", "0.8px")
            .style("cursor", "pointer")
            .on("mouseover", function(event, d) {
                if(estadoAtivo) return; 
                d3.select(this).style("filter", "brightness(0.8)"); // Em vez de cor fixa, apenas escurece no hover
                
                const nota = notasData.estados[d.properties.sigla];
                const notaText = nota ? nota.toFixed(2) : "N/D";
                
                tooltip.style("opacity", 1).html(
                    `<b>${d.properties.name}</b><br><span style="font-size:0.8rem; font-weight:600;">Nota Média: ${notaText} / 5</span>`
                );
            })
            .on("mousemove", function(event) {
                if(estadoAtivo) return;
                const [x, y] = d3.pointer(event, container);
                tooltip.style("left", x + "px").style("top", y + "px");
            })
            .on("mouseout", function() {
                if(estadoAtivo) return;
                d3.select(this).style("filter", "none");
                tooltip.style("opacity", 0);
            })
            .on("click", function(event, d) {
                if (estadoAtivo === d) return; 
                estadoAtivo = d;
                tooltip.style("opacity", 0);
            
                const bounds = path.bounds(d);
                const dx = bounds[1][0] - bounds[0][0];
                const dy = bounds[1][1] - bounds[0][1];
                const x = (bounds[0][0] + bounds[1][0]) / 2;
                const y = (bounds[0][1] + bounds[1][1]) / 2;
                const scale = Math.max(1, Math.min(8, 0.9 / Math.max(dx / width, dy / height)));
                const translate = [width / 2 - scale * x, height / 2 - scale * y];
            
                g.transition().duration(750).attr("transform", "translate(" + translate + ")scale(" + scale + ")")
                 .on("end", () => {
                     const ufCode = siglaParaCodigo[d.properties.sigla]; 
                     carregarMunicipios(ufCode, scale, notasData, colorScale);
                 });
            
                gEstados.selectAll("path").transition().duration(750).style("fill", "#eef2f5").style("stroke", "#d8d2c4");
                btnVoltar.style("display", "block");
            });

        // ==========================
        // 2. DESENHAR OS MUNICÍPIOS
        // ==========================
        function carregarMunicipios(ufCode, scale, notasData, colorScale) {
            gMunicipios.selectAll("*").remove(); 
            const urlMunicipios = `https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-${ufCode}-mun.json`;
        
            d3.json(urlMunicipios).then(dataMun => {
                gMunicipios.selectAll("path")
                    .data(dataMun.features)
                    .enter()
                    .append("path")
                    .attr("d", path)
                    .style("fill", d => {
                        const nota = notasData.municipios[d.properties.id];
                        return nota ? colorScale(nota) : "var(--accent)";
                    })
                    .style("stroke", "#ffffff")
                    .style("stroke-width", (0.5 / scale) + "px") 
                    .style("cursor", "pointer")
                    .on("mouseover", function(event, d) {
                        d3.select(this).style("filter", "brightness(0.8)").raise(); 
                        
                        const nota = notasData.municipios[d.properties.id];
                        const notaText = nota ? nota.toFixed(2) : "N/D";

                        tooltip.style("opacity", 1).html(
                            `<b>${d.properties.name}</b><br><span style="font-size:0.75rem; font-weight:400;">Cód IBGE: ${d.properties.id}</span><br><span style="font-size:0.8rem; font-weight:700;">Nota Geral: ${notaText} / 5</span>`
                        );
                    })
                    .on("mousemove", function(event) {
                        const [x, y] = d3.pointer(event, container);
                        tooltip.style("left", x + "px").style("top", y + "px");
                    })
                    .on("mouseout", function() {
                        d3.select(this).style("filter", "none");
                        tooltip.style("opacity", 0);
                    })
                    .on("click", function(event, d) {
                        const codigoIbge = d.properties.id;
                        const baseUrl = window.URL_BASE_MAPA || '/municipio/'; 
                        if (codigoIbge) window.location.href = baseUrl + codigoIbge;
                    });
            });
        }
        
        // ==========================
        // 3. RESET DO ZOOM
        // ==========================
        btnVoltar.on("click", () => {
            estadoAtivo = null;
            btnVoltar.style("display", "none");
            tooltip.style("opacity", 0);
            gMunicipios.selectAll("*").remove();
            gEstados.selectAll("path").transition().duration(750)
                .style("fill", d => {
                    const nota = notasData.estados[d.properties.sigla];
                    return nota ? colorScale(nota) : "var(--accent)";
                })
                .style("stroke", "#ffffff");
            g.transition().duration(750).attr("transform", "");
        });

        // ==========================
        // 4. FUNÇÃO DE CORRELAÇÃO DO FADE (ISOLADA POR PÁGINA)
        // ==========================
        window.dispararFadeSplash = function() {
            // Se o mapa ainda não terminou de ser desenhado pelo D3, interrompe
            if (!window.mapaDesenhado) return;
            
            // ATENÇÃO: Só bloqueia o fade se a página atual marcar que REQUER a rolagem e ela não terminou
            if (window.REQUER_ROLAGEM_MAPA && !window.rolagemMapaConcluida) return;
            
            const splash = document.getElementById('map-splash');
            if (splash) {
                splash.style.opacity = '0'; // Dispara a transição de 2 segundos
                setTimeout(() => splash.remove(), 2000); // Remove o elemento após a animação
            }
        };

        // Sinaliza que o D3 terminou de construir os elementos gráficos do mapa
        window.mapaDesenhado = true;
        
        // Tenta executar o fade imediatamente (vai funcionar direto nas telas de comparação)
        window.dispararFadeSplash();

    }).catch(err => console.error("Erro ao carregar dados do mapa:", err));
});