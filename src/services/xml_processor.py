import xml.etree.ElementTree as ET
from src.models.nfe import NotaFiscal, ItemNotaFiscal
from datetime import datetime

class XMLProcessor:
    def __init__(self):
        # CFOPs de Saída (Remessa para Consignação)
        self.cfops_saida = ["5917", "6917"]
        # CFOPs de Entrada (Retorno de Consignação)
        self.cfops_retorno = ["1918", "2918"]
        # CFOPs de Entrada (Devolução Simbólica pré-faturamento)
        self.cfops_devolucao_simbolica = ["1919", "2919"]
        # CFOPs de Entrada (Venda de Mercadoria Consignada)
        self.cfops_venda_consignada = ["5114", "6114"]

    def parse_nfe_xml(self, xml_content):
        try:
            root = ET.fromstring(xml_content)
            ns = {
                "nfe": "http://www.portalfiscal.inf.br/nfe",
                "xsi": "http://www.w3.org/2001/XMLSchema-instance"
            }

            # Dados da NF-e
            ide = root.find(".//nfe:ide", ns)
            emit = root.find(".//nfe:emit", ns)
            dest = root.find(".//nfe:dest", ns)

            numero_nf = ide.find("nfe:nNF", ns).text
            serie = ide.find("nfe:serie", ns).text
            chave_acesso = root.find(".//nfe:infNFe", ns).get("Id")[3:] # Remove "NFe"
            cfop = root.find(".//nfe:prod/nfe:CFOP", ns).text # Pega o CFOP do primeiro produto
            data_emissao_str = ide.find("nfe:dhEmi", ns).text
            data_emissao = datetime.fromisoformat(data_emissao_str.replace("Z", "+00:00"))

            cnpj_destinatario = dest.find("nfe:CNPJ", ns).text if dest.find("nfe:CNPJ", ns) is not None else \
                                dest.find("nfe:CPF", ns).text
            nome_destinatario = dest.find("nfe:xNome", ns).text

            # Tipo de Operação
            tipo_operacao = self._determine_operation_type(cfop)

            # Itens da NF-e
            itens = []
            for det in root.findall(".//nfe:det", ns):
                prod = det.find("nfe:prod", ns)
                codigo_produto = prod.find("nfe:cProd", ns).text
                descricao_produto = prod.find("nfe:xProd", ns).text
                quantidade = float(prod.find("nfe:qCom", ns).text)
                valor_unitario = float(prod.find("nfe:vUnCom", ns).text)
                valor_total = float(prod.find("nfe:vProd", ns).text)

                # Lote (se existir, pode estar em diferentes tags dependendo da NF-e)
                numero_lote = None
                # Tentativa 1: tag rastro
                rastro = prod.find("nfe:rastro", ns)
                if rastro is not None and rastro.find("nfe:nLote", ns) is not None:
                    numero_lote = rastro.find("nfe:nLote", ns).text
                # Tentativa 2: tag xLote (usada em algumas NFs)
                elif prod.find("nfe:xLote", ns) is not None:
                    numero_lote = prod.find("nfe:xLote", ns).text
                # Tentativa 3: tag nLote (usada em algumas NFs)
                elif prod.find("nfe:nLote", ns) is not None:
                    numero_lote = prod.find("nfe:nLote", ns).text

                itens.append({
                    "codigo_produto": codigo_produto,
                    "descricao_produto": descricao_produto,
                    "numero_lote": numero_lote,
                    "quantidade": quantidade,
                    "valor_unitario": valor_unitario,
                    "valor_total": valor_total
                })

            return {
                "sucesso": True,
                "dados_nfe": {
                    "numero_nf": numero_nf,
                    "serie": serie,
                    "chave_acesso": chave_acesso,
                    "cnpj_destinatario": cnpj_destinatario,
                    "nome_destinatario": nome_destinatario,
                    "cfop": cfop,
                    "data_emissao": data_emissao,
                    "itens": itens
                },
                "tipo_operacao": tipo_operacao,
                "itens_processados": len(itens)
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": f"Erro ao processar XML: {e}"
            }

    def _determine_operation_type(self, cfop):
        if cfop in self.cfops_saida:
            return "SAIDA"
        elif cfop in self.cfops_retorno:
            return "ENTRADA_RETORNO"
        elif cfop in self.cfops_devolucao_simbolica:
            return "ENTRADA_DEVOLUCAO"
        elif cfop in self.cfops_venda_consignada:
            return "ENTRADA_VENDA"
        else:
            # Default para outros CFOPs de entrada não específicos de consignação
            if cfop.startswith("1") or cfop.startswith("2"):
                return "ENTRADA"
            # Default para outros CFOPs de saída não específicos de consignação
            elif cfop.startswith("5") or cfop.startswith("6"):
                return "SAIDA"
            return "DESCONHECIDO"


