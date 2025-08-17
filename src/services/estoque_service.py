from src.extensions import db
from src.models.nfe import NotaFiscal, ItemNotaFiscal, EstoqueConsignacao
from sqlalchemy.exc import IntegrityError

class EstoqueService:
    def __init__(self):
        pass

    def processar_nfe(self, dados_nfe, tipo_operacao):
        try:
            # Verifica se a NF-e já existe para evitar duplicidade
            existing_nfe = NotaFiscal.query.filter_by(chave_acesso=dados_nfe["chave_acesso"]).first()
            if existing_nfe:
                return {"sucesso": False, "erro": "NF-e já processada anteriormente.", "nfe_id": existing_nfe.id}

            nfe = NotaFiscal(
                numero_nf=dados_nfe["numero_nf"],
                serie=dados_nfe["serie"],
                chave_acesso=dados_nfe["chave_acesso"],
                cnpj_destinatario=dados_nfe["cnpj_destinatario"],
                nome_destinatario=dados_nfe["nome_destinatario"],
                cfop=dados_nfe["cfop"],
                tipo_operacao=tipo_operacao,
                data_emissao=dados_nfe["data_emissao"],
                xml_content=dados_nfe["xml_content"]
            )
            db.session.add(nfe)
            db.session.flush() # Para ter acesso ao nfe.id antes do commit

            itens_processados = 0
            for item_data in dados_nfe["itens"]:
                item_nfe = ItemNotaFiscal(
                    nota_fiscal_id=nfe.id,
                    codigo_produto=item_data["codigo_produto"],
                    descricao_produto=item_data["descricao_produto"],
                    numero_lote=item_data["numero_lote"],
                    quantidade=item_data["quantidade"],
                    valor_unitario=item_data["valor_unitario"],
                    valor_total=item_data["valor_total"]
                )
                db.session.add(item_nfe)

                # Atualiza o estoque de consignação
                self._atualizar_estoque_consignacao(
                    item_data["codigo_produto"],
                    item_data["descricao_produto"],
                    item_data["numero_lote"],
                    dados_nfe["cnpj_destinatario"],
                    dados_nfe["nome_destinatario"],
                    item_data["quantidade"],
                    tipo_operacao,
                    nfe,
                    dados_nfe.get("nf_saida_referenciada_chave_acesso") # Passa a chave da NF de saída referenciada
                )
                itens_processados += 1

            db.session.commit()
            return {"sucesso": True, "nfe_id": nfe.id, "itens_processados": itens_processados}

        except IntegrityError:
            db.session.rollback()
            return {"sucesso": False, "erro": "Erro de integridade: Chave de acesso duplicada ou dados inválidos."}
        except Exception as e:
            db.session.rollback()
            return {"sucesso": False, "erro": f"Erro ao salvar NF-e e atualizar estoque: {e}"}

    def _atualizar_estoque_consignacao(self, codigo_produto, descricao_produto, numero_lote, cnpj_destinatario, nome_destinatario, quantidade, tipo_operacao, nfe, nf_saida_referenciada_chave_acesso=None):
        # Se for SAIDA, cria um novo registro de estoque por NF
        if tipo_operacao == "SAIDA":
            estoque = EstoqueConsignacao(
                codigo_produto=codigo_produto,
                descricao_produto=descricao_produto,
                numero_lote=numero_lote,
                cnpj_destinatario=cnpj_destinatario,
                nome_destinatario=nome_destinatario,
                quantidade_consignada_nf=quantidade,
                saldo_disponivel_nf=quantidade,
                nf_saida_id=nfe.id
            )
            db.session.add(estoque)
        else:
            # Para ENTRADA_RETORNO, ENTRADA_DEVOLUCAO, ENTRADA_VENDA, precisamos encontrar a NF de SAIDA original
            # A NF de entrada/retorno/venda DEVE referenciar a NF de saída original (ex: pela chave de acesso)
            if not nf_saida_referenciada_chave_acesso:
                raise ValueError("Para operações de ENTRADA (RETORNO, DEVOLUCAO, VENDA), a chave de acesso da NF de saída referenciada é obrigatória.")

            # Busca a NF de saída original
            nf_saida_original = NotaFiscal.query.filter_by(chave_acesso=nf_saida_referenciada_chave_acesso, tipo_operacao="SAIDA").first()
            if not nf_saida_original:
                raise ValueError(f"NF de Saída original com chave {nf_saida_referenciada_chave_acesso} não encontrada.")

            # Encontra o registro de EstoqueConsignacao correspondente à NF de saída original
            estoque = EstoqueConsignacao.query.filter_by(
                nf_saida_id=nf_saida_original.id,
                codigo_produto=codigo_produto,
                numero_lote=numero_lote,
                cnpj_destinatario=cnpj_destinatario
            ).first()

            if not estoque:
                # Isso pode acontecer se a NF de saída original não foi processada ou se os dados não batem
                raise ValueError(f"Registro de estoque consignado para NF de saída {nf_saida_original.numero_nf} e produto {codigo_produto} não encontrado.")

            if tipo_operacao == "ENTRADA_RETORNO":
                estoque.quantidade_retornada_nf += quantidade
            elif tipo_operacao == "ENTRADA_DEVOLUCAO":
                estoque.quantidade_retornada_nf += quantidade # Devolução simbólica também reduz o saldo consignado
            elif tipo_operacao == "ENTRADA_VENDA":
                estoque.quantidade_faturada_nf += quantidade

            estoque.saldo_disponivel_nf = estoque.quantidade_consignada_nf - estoque.quantidade_retornada_nf - estoque.quantidade_faturada_nf

    def get_resumo_estoque(self):
        # Este método agora pode ser mais complexo, somando saldos por produto/destinatário
        # ou pode ser removido se a granularidade por NF for a principal
        total_produtos = EstoqueConsignacao.query.distinct(EstoqueConsignacao.codigo_produto).count()
        total_destinatarios = EstoqueConsignacao.query.distinct(EstoqueConsignacao.cnpj_destinatario).count()
        saldo_total_disponivel = db.session.query(db.func.sum(EstoqueConsignacao.saldo_disponivel_nf)).scalar() or 0
        
        # Produtos com saldo baixo pode ser mais complexo agora, talvez por NF ou por produto geral
        # Por simplicidade, vamos manter a soma geral por enquanto
        produtos_saldo_baixo = EstoqueConsignacao.query.filter(EstoqueConsignacao.saldo_disponivel_nf < 10, EstoqueConsignacao.saldo_disponivel_nf > 0).count()

        return {
            "total_produtos": total_produtos,
            "total_destinatarios": total_destinatarios,
            "saldo_total_disponivel": saldo_total_disponivel,
            "produtos_saldo_baixo": produtos_saldo_baixo
        }

    def get_saldo_por_destinatario(self, cnpj):
        # Retorna todos os registros de estoque para um CNPJ, incluindo detalhes da NF de saída
        saldos = EstoqueConsignacao.query.filter_by(cnpj_destinatario=cnpj).all()
        results = []
        for s in saldos:
            nf_saida = NotaFiscal.query.get(s.nf_saida_id)
            results.append({
                "codigo_produto": s.codigo_produto,
                "descricao_produto": s.descricao_produto,
                "numero_lote": s.numero_lote,
                "quantidade_consignada_nf": s.quantidade_consignada_nf,
                "quantidade_retornada_nf": s.quantidade_retornada_nf,
                "quantidade_faturada_nf": s.quantidade_faturada_nf,
                "saldo_disponivel_nf": s.saldo_disponivel_nf,
                "nf_saida_numero": nf_saida.numero_nf if nf_saida else None,
                "nf_saida_data_emissao": nf_saida.data_emissao.strftime("%Y-%m-%d") if nf_saida else None
            })
        return results

    def get_saldo_por_produto(self, codigo_produto):
        # Retorna todos os registros de estoque para um produto, incluindo detalhes da NF de saída
        saldos = EstoqueConsignacao.query.filter_by(codigo_produto=codigo_produto).all()
        results = []
        for s in saldos:
            nf_saida = NotaFiscal.query.get(s.nf_saida_id)
            results.append({
                "cnpj_destinatario": s.cnpj_destinatario,
                "nome_destinatario": s.nome_destinatario,
                "numero_lote": s.numero_lote,
                "quantidade_consignada_nf": s.quantidade_consignada_nf,
                "quantidade_retornada_nf": s.quantidade_retornada_nf,
                "quantidade_faturada_nf": s.quantidade_faturada_nf,
                "saldo_disponivel_nf": s.saldo_disponivel_nf,
                "nf_saida_numero": nf_saida.numero_nf if nf_saida else None,
                "nf_saida_data_emissao": nf_saida.data_emissao.strftime("%Y-%m-%d") if nf_saida else None
            })
        return results

    def validar_disponibilidade_faturamento(self, cnpj_destinatario, itens_faturamento):
        erros = []
        for item_req in itens_faturamento:
            # Para validar faturamento, agora precisamos saber qual NF de saída está sendo faturada
            # ou somar o saldo total disponível para o produto/lote/destinatário
            # Por simplicidade, vamos somar o saldo total para o produto/lote/destinatário
            total_saldo_produto = db.session.query(db.func.sum(EstoqueConsignacao.saldo_disponivel_nf)).filter_by(
                cnpj_destinatario=cnpj_destinatario,
                codigo_produto=item_req["codigo_produto"],
                numero_lote=item_req["numero_lote"]
            ).scalar() or 0

            if total_saldo_produto < item_req["quantidade"]:
                erros.append(f"Produto {item_req["codigo_produto"]} (Lote: {item_req["numero_lote"]}) não possui saldo suficiente para faturamento no destinatário {cnpj_destinatario}.")
        
        return {"sucesso": len(erros) == 0, "erros": erros}





