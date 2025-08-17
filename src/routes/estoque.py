from flask import Blueprint, request, jsonify
from src.services.xml_processor import XMLProcessor
from src.services.estoque_service import EstoqueService
from src.services.maino_api import MainoAPI
from src.models.nfe import NotaFiscal
from datetime import datetime, timedelta

estoque_bp = Blueprint("estoque", __name__)

xml_processor = XMLProcessor()
estoque_service = EstoqueService()
maino_api = MainoAPI()

@estoque_bp.route("/teste", methods=["GET"])
def teste():
    return jsonify({"status": "ok", "message": "API de Estoque funcionando"})

@estoque_bp.route("/resumo", methods=["GET"])
def resumo():
    resumo_data = estoque_service.get_resumo_estoque()
    return jsonify(resumo_data)

@estoque_bp.route("/processar-xml", methods=["POST"])
def processar_xml():
    data = request.get_json()
    xml_content = data.get("xml_content")
    
    if not xml_content:
        return jsonify({"sucesso": False, "erro": "Conteúdo XML não fornecido"}), 400
    
    # Processa o XML
    resultado_xml = xml_processor.parse_nfe_xml(xml_content)
    
    if not resultado_xml["sucesso"]:
        return jsonify(resultado_xml), 400
    
    # Adiciona o XML content aos dados da NF-e
    resultado_xml["dados_nfe"]["xml_content"] = xml_content

    # Tenta extrair a chave de acesso da NF de saída referenciada do XML
    nf_saida_referenciada_chave_acesso = xml_processor.extract_referenced_nfe_chave_acesso(xml_content)
    if nf_saida_referenciada_chave_acesso:
        resultado_xml["dados_nfe"]["nf_saida_referenciada_chave_acesso"] = nf_saida_referenciada_chave_acesso
    
    # Salva no banco de dados
    try:
        resultado_estoque = estoque_service.processar_nfe(
            resultado_xml["dados_nfe"], 
            resultado_xml["tipo_operacao"]
        )
    except ValueError as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 400

    if not resultado_estoque["sucesso"]:
        return jsonify(resultado_estoque), 400
    
    return jsonify({
        "sucesso": True,
        "dados_nfe": resultado_xml["dados_nfe"],
        "tipo_operacao": resultado_xml["tipo_operacao"],
        "itens_processados": resultado_estoque["itens_processados"],
        "nfe_id": resultado_estoque["nfe_id"]
    })

@estoque_bp.route("/saldo-destinatario/<cnpj>", methods=["GET"])
def saldo_destinatario(cnpj):
    saldos = estoque_service.get_saldo_por_destinatario(cnpj)
    return jsonify({"saldos": saldos})

@estoque_bp.route("/saldo-produto/<codigo_produto>", methods=["GET"])
def saldo_produto(codigo_produto):
    saldos = estoque_service.get_saldo_por_produto(codigo_produto)
    return jsonify({"saldos": saldos})

@estoque_bp.route("/validar-faturamento", methods=["POST"])
def validar_faturamento():
    data = request.get_json()
    cnpj_destinatario = data.get("cnpj_destinatario")
    itens = data.get("itens", [])
    
    if not cnpj_destinatario or not itens:
        return jsonify({"sucesso": False, "erro": "CNPJ do destinatário e itens são obrigatórios"}), 400
    
    resultado = estoque_service.validar_disponibilidade_faturamento(cnpj_destinatario, itens)
    return jsonify(resultado)

@estoque_bp.route("/sincronizar-maino", methods=["POST"])
def sincronizar_maino():
    data = request.get_json()
    dias_atras = data.get("dias_atras", 7)
    
    try:
        # Testa a conexão
        teste_conexao = maino_api.test_connection()
        if not teste_conexao["sucesso"]:
            return jsonify(teste_conexao), 400
        
        # Busca NF-es emitidas do período
        end_date = datetime.now()
        start_date = end_date - timedelta(days=dias_atras)
        resultado_nfes = maino_api.get_nfes_emitidas(start_date, end_date)

        if not resultado_nfes["sucesso"]:
            return jsonify(resultado_nfes), 400
        
        nfes_para_processar = resultado_nfes["nfes"]
        
        xmls_processados = 0
        nfes_saida = 0
        nfes_entrada = 0
        erros = []
        
        for nfe_item in nfes_para_processar:
            chave_acesso = nfe_item.get("chaveAcesso")
            if not chave_acesso:
                erros.append(f"NF-e sem chave de acesso: {nfe_item.get("numero")}")
                continue

            # Busca o XML completo da NF-e
            resultado_xml_completo = maino_api.get_nfe_xml_by_chave(chave_acesso)
            if not resultado_xml_completo["sucesso"]:
                erros.append(f"Erro ao buscar XML da NF-e {chave_acesso}: {resultado_xml_completo["erro"]}")
                continue
            xml_content = resultado_xml_completo["xml_content"]

            # Processa o XML
            resultado_xml = xml_processor.parse_nfe_xml(xml_content)
            
            if resultado_xml["sucesso"]:
                # Adiciona o XML content aos dados da NF-e
                resultado_xml["dados_nfe"]["xml_content"] = xml_content

                # Tenta extrair a chave de acesso da NF de saída referenciada do XML
                nf_saida_referenciada_chave_acesso = xml_processor.extract_referenced_nfe_chave_acesso(xml_content)
                if nf_saida_referenciada_chave_acesso:
                    resultado_xml["dados_nfe"]["nf_saida_referenciada_chave_acesso"] = nf_saida_referenciada_chave_acesso
                
                # Salva no banco de dados
                try:
                    resultado_estoque = estoque_service.processar_nfe(
                        resultado_xml["dados_nfe"], 
                        resultado_xml["tipo_operacao"]
                    )
                except ValueError as e:
                    erros.append(f"NF {resultado_xml["dados_nfe"]["numero_nf"]}: {str(e)}")
                    continue
                
                if resultado_estoque["sucesso"]:
                    xmls_processados += 1
                    if resultado_xml["tipo_operacao"] == "SAIDA":
                        nfes_saida += 1
                    else:
                        nfes_entrada += 1
                else:
                    erros.append(f"NF {resultado_xml["dados_nfe"]["numero_nf"]}: {resultado_estoque["erro"]}")
            else:
                erros.append(f"Erro ao processar XML: {resultado_xml["erro"]}")
        
        return jsonify({
            "sucesso": True,
            "nfes_encontradas": len(nfes_para_processar),
            "nfes_processadas": xmls_processados,
            "nfes_saida": nfes_saida,
            "nfes_entrada": nfes_entrada,
            "erros": erros
        })
        
    except ValueError as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 400
    except Exception as e:
        return jsonify({"sucesso": False, "erro": f"Erro interno: {e}"}), 500

@estoque_bp.route("/status-integracao", methods=["GET"])
def status_integracao():
    try:
        teste_conexao = maino_api.test_connection()
        
        return jsonify({
            "integração_configurada": True,
            "conexao_api": teste_conexao["sucesso"],
            "ultima_sincronizacao": None  # Pode ser implementado para armazenar a última sincronização
        })
        
    except ValueError:
        return jsonify({
            "integração_configurada": False,
            "conexao_api": False,
            "ultima_sincronizacao": None
        })
    except Exception as e:
        return jsonify({
            "integração_configurada": True,
            "conexao_api": False,
            "erro": str(e),
            "ultima_sincronizacao": None
        })



