from flask import Blueprint, request, jsonify
from src.services.xml_processor import XMLProcessor
from src.services.estoque_service import EstoqueService
from src.services.maino_api import MainoAPI

estoque_bp = Blueprint("estoque", __name__)

xml_processor = XMLProcessor()
estoque_service = EstoqueService()

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
    
    # Salva no banco de dados
    resultado_estoque = estoque_service.processar_nfe(
        resultado_xml["dados_nfe"], 
        resultado_xml["tipo_operacao"]
    )
    
    if not resultado_estoque["sucesso"]:
        return jsonify(resultado_estoque), 400
    
    return jsonify({
        "sucesso": True,
        "dados_nfe": resultado_xml["dados_nfe"],
        "tipo_operacao": resultado_xml["tipo_operacao"],
        "itens_processados": resultado_xml["itens_processados"],
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
        maino_api = MainoAPI()
        
        # Testa a conexão
        teste_conexao = maino_api.test_connection()
        if not teste_conexao["sucesso"]:
            return jsonify(teste_conexao), 400
        
        # Busca XMLs do período
        resultado_zip = maino_api.get_nfes_xml_in_period(dias_atras)
        if not resultado_zip["sucesso"]:
            return jsonify(resultado_zip), 400
        
        # Extrai XMLs do ZIP
        xml_contents = maino_api.extract_xmls_from_zip(resultado_zip["zip_content"])
        
        xmls_processados = 0
        nfes_saida = 0
        nfes_entrada = 0
        erros = []
        
        for xml_content in xml_contents:
            # Processa cada XML
            resultado_xml = xml_processor.parse_nfe_xml(xml_content)
            
            if resultado_xml["sucesso"]:
                # Adiciona o XML content aos dados da NF-e
                resultado_xml["dados_nfe"]["xml_content"] = xml_content
                
                # Salva no banco de dados
                resultado_estoque = estoque_service.processar_nfe(
                    resultado_xml["dados_nfe"], 
                    resultado_xml["tipo_operacao"]
                )
                
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
            "xmls_encontrados": len(xml_contents),
            "xmls_processados": xmls_processados,
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
        maino_api = MainoAPI()
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

