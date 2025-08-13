document.addEventListener("DOMContentLoaded", () => {
    const API_BASE_URL = window.location.origin; // Usa a origem atual para a API

    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");
    const loadingModal = document.getElementById("loading-modal");
    const loadingText = document.getElementById("loading-text");
    const toastContainer = document.getElementById("toast-container");

    // Função para mostrar toast
    function showToast(message, type = "success") {
        const toast = document.createElement("div");
        toast.className = `p-3 rounded-lg shadow-md text-white flex items-center fade-in`;
        if (type === "success") {
            toast.classList.add("bg-green-500");
            toast.innerHTML = `<i class="fas fa-check-circle mr-2"></i>${message}`;
        } else if (type === "error") {
            toast.classList.add("bg-red-500");
            toast.innerHTML = `<i class="fas fa-times-circle mr-2"></i>${message}`;
        } else if (type === "info") {
            toast.classList.add("bg-blue-500");
            toast.innerHTML = `<i class="fas fa-info-circle mr-2"></i>${message}`;
        }
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.classList.remove("fade-in");
            toast.classList.add("fade-out"); // Adicionar classe para fade-out se necessário
            toast.remove();
        }, 5000);
    }

    // Função para mostrar/esconder modal de carregamento
    function toggleLoading(show, message = "Processando...") {
        loadingText.textContent = message;
        if (show) {
            loadingModal.classList.remove("hidden");
            loadingModal.classList.add("flex");
        } else {
            loadingModal.classList.add("hidden");
            loadingModal.classList.remove("flex");
        }
    }

    // Ativar tab
    tabButtons.forEach(button => {
        button.addEventListener("click", () => {
            tabButtons.forEach(btn => {
                btn.classList.remove("active", "border-blue-500", "text-blue-600");
                btn.classList.add("border-transparent", "text-gray-500", "hover:text-gray-700");
            });
            tabContents.forEach(content => content.classList.add("hidden"));

            button.classList.add("active", "border-blue-500", "text-blue-600");
            button.classList.remove("border-transparent", "text-gray-500", "hover:text-gray-700");

            document.getElementById(`${button.dataset.tab}-tab`).classList.remove("hidden");
            
            // Carregar dados específicos da tab
            if (button.dataset.tab === "dashboard") {
                fetchDashboardData();
            } else if (button.dataset.tab === "integracao") {
                fetchIntegracaoStatus();
            }
        });
    });

    // Fetch Dashboard Data
    async function fetchDashboardData() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/estoque/resumo`);
            const data = await response.json();
            document.getElementById("total-produtos").textContent = data.total_produtos;
            document.getElementById("total-destinatarios").textContent = data.total_destinatarios;
            document.getElementById("saldo-total").textContent = data.saldo_total_disponivel.toFixed(2);
            document.getElementById("saldo-baixo").textContent = data.produtos_saldo_baixo;

            // Placeholder para produtos com saldo baixo e últimas movimentações
            document.getElementById("produtos-saldo-baixo").innerHTML = 
                `<p class="text-gray-500">Funcionalidade a ser implementada.</p>`;
            document.getElementById("ultimas-movimentacoes").innerHTML = 
                `<p class="text-gray-500">Funcionalidade a ser implementada.</p>`;

        } catch (error) {
            console.error("Erro ao buscar dados do dashboard:", error);
            showToast("Erro ao carregar dados do dashboard.", "error");
        }
    }

    // Processar XML
    document.getElementById("processar-xml").addEventListener("click", async () => {
        const xmlContent = document.getElementById("xml-content").value;
        if (!xmlContent) {
            showToast("Por favor, cole o conteúdo do XML.", "error");
            return;
        }

        toggleLoading(true, "Processando XML...");
        try {
            const response = await fetch(`${API_BASE_URL}/api/estoque/processar-xml`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ xml_content: xmlContent })
            });
            const result = await response.json();

            const resultadoXmlDiv = document.getElementById("resultado-xml");
            const xmlDetailsDiv = document.getElementById("xml-details");
            resultadoXmlDiv.classList.remove("hidden");

            if (result.sucesso) {
                resultadoXmlDiv.classList.remove("bg-red-100");
                resultadoXmlDiv.classList.add("bg-green-100");
                xmlDetailsDiv.innerHTML = `
                    <p><strong>Status:</strong> <span class="text-green-700">Sucesso</span></p>
                    <p><strong>NF-e Processada:</strong> ${result.dados_nfe.numero_nf}</p>
                    <p><strong>Tipo de Operação:</strong> ${result.tipo_operacao}</p>
                    <p><strong>Itens Processados:</strong> ${result.itens_processados}</p>
                    <p><strong>Chave de Acesso:</strong> ${result.dados_nfe.chave_acesso}</p>
                    <p><strong>Destinatário:</strong> ${result.dados_nfe.nome_destinatario} (${result.dados_nfe.cnpj_destinatario})</p>
                `;
                showToast("XML processado com sucesso!", "success");
            } else {
                resultadoXmlDiv.classList.remove("bg-green-100");
                resultadoXmlDiv.classList.add("bg-red-100");
                xmlDetailsDiv.innerHTML = `
                    <p><strong>Status:</strong> <span class="text-red-700">Erro</span></p>
                    <p><strong>Mensagem:</strong> ${result.erro}</p>
                `;
                showToast(`Erro: ${result.erro}`, "error");
            }
        } catch (error) {
            console.error("Erro ao processar XML:", error);
            showToast("Erro de comunicação com a API.", "error");
        } finally {
            toggleLoading(false);
        }
    });

    // Consultar por CNPJ
    document.getElementById("consultar-cnpj").addEventListener("click", async () => {
        const cnpj = document.getElementById("cnpj-input").value;
        if (!cnpj) {
            showToast("Por favor, digite o CNPJ.", "error");
            return;
        }
        toggleLoading(true, "Consultando por CNPJ...");
        try {
            const response = await fetch(`${API_BASE_URL}/api/estoque/saldo-destinatario/${cnpj}`);
            const result = await response.json();
            renderConsultaResults(result.saldos);
            showToast("Consulta por CNPJ concluída.", "info");
        } catch (error) {
            console.error("Erro ao consultar CNPJ:", error);
            showToast("Erro ao consultar por CNPJ.", "error");
        } finally {
            toggleLoading(false);
        }
    });

    // Consultar por Produto
    document.getElementById("consultar-produto").addEventListener("click", async () => {
        const produto = document.getElementById("produto-input").value;
        if (!produto) {
            showToast("Por favor, digite o código do produto.", "error");
            return;
        }
        toggleLoading(true, "Consultando por Produto...");
        try {
            const response = await fetch(`${API_BASE_URL}/api/estoque/saldo-produto/${produto}`);
            const result = await response.json();
            renderConsultaResults(result.saldos);
            showToast("Consulta por Produto concluída.", "info");
        } catch (error) {
            console.error("Erro ao consultar produto:", error);
            showToast("Erro ao consultar por produto.", "error");
        } finally {
            toggleLoading(false);
        }
    });

    function renderConsultaResults(saldos) {
        const tabelaResultados = document.getElementById("tabela-resultados");
        const resultadosConsultaDiv = document.getElementById("resultados-consulta");
        tabelaResultados.innerHTML = ""; // Limpa resultados anteriores

        if (saldos.length === 0) {
            tabelaResultados.innerHTML = `<tr><td colspan="7" class="px-6 py-4 text-center text-gray-500">Nenhum resultado encontrado.</td></tr>`;
            resultadosConsultaDiv.classList.remove("hidden");
            return;
        }

        saldos.forEach(item => {
            const row = document.createElement("tr");
            row.className = "hover:bg-gray-50";
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${item.descricao_produto} (${item.codigo_produto})</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${item.numero_lote || "N/A"}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${item.nome_destinatario || item.cnpj_destinatario}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${item.quantidade_enviada}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${item.quantidade_retornada}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${item.quantidade_faturada}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-bold ${item.saldo_disponivel > 0 ? 'text-green-600' : 'text-red-600'}">${item.saldo_disponivel}</td>
            `;
            tabelaResultados.appendChild(row);
        });
        resultadosConsultaDiv.classList.remove("hidden");
    }

    // Sincronizar com Mainô
    document.getElementById("sincronizar-manual").addEventListener("click", async () => {
        const diasSync = document.getElementById("dias-sync").value;
        toggleLoading(true, `Sincronizando NF-es dos últimos ${diasSync} dias...`);
        try {
            const response = await fetch(`${API_BASE_URL}/api/estoque/sincronizar-maino`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ dias_atras: parseInt(diasSync) })
            });
            const result = await response.json();

            const resultadoSyncDiv = document.getElementById("resultado-sync");
            const syncDetailsDiv = document.getElementById("sync-details");
            resultadoSyncDiv.classList.remove("hidden");

            if (result.sucesso) {
                syncDetailsDiv.innerHTML = `
                    <p><strong>Status:</strong> <span class="text-green-700">Sucesso</span></p>
                    <p><strong>XMLs Encontrados:</strong> ${result.xmls_encontrados}</p>
                    <p><strong>XMLs Processados:</strong> ${result.xmls_processados}</p>
                    <p><strong>NF-es de Saída:</strong> ${result.nfes_saida}</p>
                    <p><strong>NF-es de Entrada:</strong> ${result.nfes_entrada}</p>
                    ${result.erros.length > 0 ? `<p class="text-red-600"><strong>Erros:</strong> ${result.erros.join(", ")}</p>` : ""}
                `;
                showToast("Sincronização concluída com sucesso!", "success");
            } else {
                syncDetailsDiv.innerHTML = `
                    <p><strong>Status:</strong> <span class="text-red-700">Erro</span></p>
                    <p><strong>Mensagem:</strong> ${result.erro}</p>
                `;
                showToast(`Erro na sincronização: ${result.erro}`, "error");
            }
        } catch (error) {
            console.error("Erro ao sincronizar com Mainô:", error);
            showToast("Erro de comunicação com a API de sincronização.", "error");
        } finally {
            toggleLoading(false);
            fetchIntegracaoStatus(); // Atualiza o status após a sincronização
        }
    });

    // Fetch Status Integração
    async function fetchIntegracaoStatus() {
        const statusIndicator = document.getElementById("status-indicator");
        const statusText = document.getElementById("status-text");
        const integracaoStatusDiv = document.getElementById("status-integracao");

        try {
            const response = await fetch(`${API_BASE_URL}/api/estoque/status-integracao`);
            const result = await response.json();

            if (result.integração_configurada) {
                if (result.conexao_api) {
                    statusIndicator.querySelector(".status-indicator").className = "status-indicator status-online";
                    statusText.textContent = "Mainô Conectado";
                    integracaoStatusDiv.innerHTML = `
                        <p><strong>Status:</strong> <span class="text-green-700">Conectado</span></p>
                        <p><strong>Mensagem:</strong> Conexão com a API do Mainô estabelecida.</p>
                    `;
                } else {
                    statusIndicator.querySelector(".status-indicator").className = "status-indicator status-warning";
                    statusText.textContent = "Mainô (Erro de Conexão)";
                    integracaoStatusDiv.innerHTML = `
                        <p><strong>Status:</strong> <span class="text-red-700">Erro de Conexão</span></p>
                        <p><strong>Mensagem:</strong> ${result.erro || "Verifique suas credenciais ou a disponibilidade da API do Mainô."}</p>
                    `;
                }
            } else {
                statusIndicator.querySelector(".status-indicator").className = "status-indicator status-offline";
                statusText.textContent = "Mainô (Não Configurado)";
                integracaoStatusDiv.innerHTML = `
                    <p><strong>Status:</strong> <span class="text-red-700">Não Configurado</span></p>
                    <p><strong>Mensagem:</strong> As variáveis de ambiente MAINO_API_KEY ou MAINO_BEARER_TOKEN não estão configuradas.</p>
                `;
            }
        } catch (error) {
            console.error("Erro ao buscar status de integração:", error);
            statusIndicator.querySelector(".status-indicator").className = "status-indicator status-offline";
            statusText.textContent = "API Offline";
            integracaoStatusDiv.innerHTML = `
                <p><strong>Status:</strong> <span class="text-red-700">API Offline</span></p>
                <p><strong>Mensagem:</strong> Não foi possível conectar à API da plataforma. Verifique se o servidor está rodando.</p>
            `;
        }
    }

    // Sincronização do botão do header
    document.getElementById("sync-btn").addEventListener("click", async () => {
        const diasSync = 7; // Sincroniza os últimos 7 dias por padrão
        toggleLoading(true, `Sincronizando NF-es dos últimos ${diasSync} dias...`);
        try {
            const response = await fetch(`${API_BASE_URL}/api/estoque/sincronizar-maino`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ dias_atras: diasSync })
            });
            const result = await response.json();
            if (result.sucesso) {
                showToast("Sincronização rápida concluída!", "success");
            } else {
                showToast(`Erro na sincronização rápida: ${result.erro}`, "error");
            }
        } catch (error) {
            console.error("Erro ao sincronizar rápido:", error);
            showToast("Erro de comunicação com a API de sincronização rápida.", "error");
        } finally {
            toggleLoading(false);
            fetchDashboardData();
            fetchIntegracaoStatus();
        }
    });

    // Inicialização
    fetchDashboardData();
    fetchIntegracaoStatus();

    // Ativar a primeira tab por padrão
    document.querySelector(".tab-btn").click();
});

