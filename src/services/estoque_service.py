from src.models.user import db
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
                    nfe
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

    def _atualizar_estoque_consignacao(self, codigo_produto, descricao_produto, numero_lote, cnpj_destinatario, nome_destinatario, quantidade, tipo_operacao, nfe):
        estoque = EstoqueConsignacao.query.filter_by(
            codigo_produto=codigo_produto,
            numero_lote=numero_lote,
            cnpj_destinatario=cnpj_destinatario
        ).first()

        if not estoque:
            estoque = EstoqueConsignacao(
                codigo_produto=codigo_produto,
                descricao_produto=descricao_produto,
                numero_lote=numero_lote,
                cnpj_destinatario=cnpj_destinatario,
                nome_destinatario=nome_destinatario,
                quantidade_enviada=0.0,
                quantidade_retornada=0.0,
                quantidade_faturada=0.0,
                saldo_disponivel=0.0
            )
            db.session.add(estoque)
            db.session.flush()

        if tipo_operacao == "SAIDA":
            estoque.quantidade_enviada += quantidade
            estoque.nf_saida_id = nfe.id
        elif tipo_operacao == "ENTRADA_RETORNO":
            estoque.quantidade_retornada += quantidade
            estoque.nf_entrada_id = nfe.id
        elif tipo_operacao == "ENTRADA_DEVOLUCAO":
            estoque.quantidade_retornada += quantidade
            estoque.nf_entrada_id = nfe.id
        elif tipo_operacao == "ENTRADA_VENDA":
            estoque.quantidade_faturada += quantidade
            estoque.nf_entrada_id = nfe.id

        estoque.saldo_disponivel = estoque.quantidade_enviada - estoque.quantidade_retornada - estoque.quantidade_faturada

    def get_resumo_estoque(self):
        total_produtos = EstoqueConsignacao.query.distinct(EstoqueConsignacao.codigo_produto).count()
        total_destinatarios = EstoqueConsignacao.query.distinct(EstoqueConsignacao.cnpj_destinatario).count()
        saldo_total_disponivel = db.session.query(db.func.sum(EstoqueConsignacao.saldo_disponivel)).scalar() or 0
        produtos_saldo_baixo = EstoqueConsignacao.query.filter(EstoqueConsignacao.saldo_disponivel < 10, EstoqueConsignacao.saldo_disponivel > 0).count()

        return {
            "total_produtos": total_produtos,
            "total_destinatarios": total_destinatarios,
            "saldo_total_disponivel": saldo_total_disponivel,
            "produtos_saldo_baixo": produtos_saldo_baixo
        }

    def get_saldo_por_destinatario(self, cnpj):
        saldos = EstoqueConsignacao.query.filter_by(cnpj_destinatario=cnpj).all()
        return [{
            "codigo_produto": s.codigo_produto,
            "descricao_produto": s.descricao_produto,
            "numero_lote": s.numero_lote,
            "quantidade_enviada": s.quantidade_enviada,
            "quantidade_retornada": s.quantidade_retornada,
            "quantidade_faturada": s.quantidade_faturada,
            "saldo_disponivel": s.saldo_disponivel
        } for s in saldos]

    def get_saldo_por_produto(self, codigo_produto):
        saldos = EstoqueConsignacao.query.filter_by(codigo_produto=codigo_produto).all()
        return [{
            "cnpj_destinatario": s.cnpj_destinatario,
            "nome_destinatario": s.nome_destinatario,
            "numero_lote": s.numero_lote,
            "quantidade_enviada": s.quantidade_enviada,
            "quantidade_retornada": s.quantidade_retornada,
            "quantidade_faturada": s.quantidade_faturada,
            "saldo_disponivel": s.saldo_disponivel
        } for s in saldos]

    def validar_disponibilidade_faturamento(self, cnpj_destinatario, itens_faturamento):
        erros = []
        for item_req in itens_faturamento:
            estoque = EstoqueConsignacao.query.filter_by(
                cnpj_destinatario=cnpj_destinatario,
                codigo_produto=item_req["codigo_produto"],
                numero_lote=item_req["numero_lote"]
            ).first()

            if not estoque or estoque.saldo_disponivel < item_req["quantidade"]:
                erros.append(f"Produto {item_req["codigo_produto"]} (Lote: {item_req["numero_lote"]}) não possui saldo suficiente para faturamento no destinatário {cnpj_destinatario}.")
        
        return {"sucesso": len(erros) == 0, "erros": erros}


