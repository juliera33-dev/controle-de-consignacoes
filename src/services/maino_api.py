import requests
import os
import zipfile
import io
from datetime import datetime, timedelta

class MainoAPI:
    def __init__(self):
        self.base_url = "https://api.maino.com.br/"
        self.api_key = os.getenv("MAINO_API_KEY")
        self.bearer_token = os.getenv("MAINO_BEARER_TOKEN")

        if not self.api_key and not self.bearer_token:
            raise ValueError("MAINO_API_KEY or MAINO_BEARER_TOKEN must be set as environment variables.")

        self.headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            self.headers["Authorization"] = f"ApiKey {self.api_key}"
        elif self.bearer_token:
            self.headers["Authorization"] = f"Bearer {self.bearer_token}"

    def test_connection(self):
        try:
            # Endpoint para testar a conexão e autenticação usando um endpoint de NF-e
            response = requests.get(f"{self.base_url}api/v1/nfe/emitidas?dataInicial=2024-01-01&dataFinal=2024-01-01", headers=self.headers, timeout=5)
            response.raise_for_status()
            return {"sucesso": True, "mensagem": "Conexão com Mainô estabelecida."}
        except requests.exceptions.RequestException as e:
            return {"sucesso": False, "erro": f"Erro de conexão com Mainô: {e}"}

    def get_nfes_emitidas(self, start_date: datetime, end_date: datetime):
        params = {
            "dataInicial": start_date.strftime("%Y-%m-%d"),
            "dataFinal": end_date.strftime("%Y-%m-%d"),
            "tipoDocumento": "NFE", # Filtrar apenas por NF-e
            "pagina": 1, # Começar na primeira página
            "limite": 100 # Limite de itens por página
        }
        nfes_data = []
        while True:
            try:
                response = requests.get(f"{self.base_url}api/v1/nfe/emitidas", headers=self.headers, params=params, timeout=60)
                response.raise_for_status()
                data = response.json()
                if not data or not data.get("itens"): # Verifica se há itens na resposta
                    break
                nfes_data.extend(data["itens"])
                if data.get("totalPaginas") and params["pagina"] < data["totalPaginas"]:
                    params["pagina"] += 1
                else:
                    break
            except requests.exceptions.RequestException as e:
                return {"sucesso": False, "erro": f"Erro ao buscar NF-es emitidas do Mainô: {e}"}
        return {"sucesso": True, "nfes": nfes_data}

    def get_nfe_xml_by_chave(self, chave_acesso: str):
        try:
            response = requests.get(f"{self.base_url}api/v1/nfe/xml?chaveAcesso={chave_acesso}", headers=self.headers, timeout=60)
            response.raise_for_status()
            return {"sucesso": True, "xml_content": response.text}
        except requests.exceptions.RequestException as e:
            return {"sucesso": False, "erro": f"Erro ao buscar XML da NF-e {chave_acesso}: {e}"}

    def extract_xmls_from_zip(self, zip_content):
        # Este método pode ser removido se não for mais usado para exportar ZIPs
        xml_contents = []
        with zipfile.ZipFile(zip_content, "r") as zf:
            for name in zf.namelist():
                if name.endswith(".xml"):
                    with zf.open(name) as xml_file:
                        xml_contents.append(xml_file.read().decode("utf-8"))
        return xml_contents




