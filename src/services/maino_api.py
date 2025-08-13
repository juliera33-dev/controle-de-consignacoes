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
            # Endpoint simples para testar a conexão e autenticação
            response = requests.get(f"{self.base_url}api/v1/empresas", headers=self.headers, timeout=5)
            response.raise_for_status()
            return {"sucesso": True, "mensagem": "Conexão com Mainô estabelecida."}
        except requests.exceptions.RequestException as e:
            return {"sucesso": False, "erro": f"Erro de conexão com Mainô: {e}"}

    def get_nfes_xml_in_period(self, days_ago=7):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_ago)

        params = {
            "dataInicial": start_date.strftime("%Y-%m-%d"),
            "dataFinal": end_date.strftime("%Y-%m-%d"),
            "tipo": "saida", # Ou "entrada" se necessário
            "formato": "xml"
        }

        try:
            response = requests.get(f"{self.base_url}api/v1/nfe/exportar", headers=self.headers, params=params, timeout=300)
            response.raise_for_status()

            if response.headers["Content-Type"] == "application/zip":
                zip_file_bytes = io.BytesIO(response.content)
                return {"sucesso": True, "zip_content": zip_file_bytes}
            else:
                return {"sucesso": False, "erro": "Resposta não é um arquivo ZIP. Verifique os parâmetros ou a API."}

        except requests.exceptions.RequestException as e:
            return {"sucesso": False, "erro": f"Erro ao exportar NF-es do Mainô: {e}"}

    def extract_xmls_from_zip(self, zip_content):
        xml_contents = []
        with zipfile.ZipFile(zip_content, "r") as zf:
            for name in zf.namelist():
                if name.endswith(".xml"):
                    with zf.open(name) as xml_file:
                        xml_contents.append(xml_file.read().decode("utf-8"))
        return xml_contents

