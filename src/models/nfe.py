from src.models.user import db
from datetime import datetime

class NotaFiscal(db.Model):
    __tablename__ = 'notas_fiscais'
    id = db.Column(db.Integer, primary_key=True)
    numero_nf = db.Column(db.String(20), nullable=False)
    serie = db.Column(db.String(5))
    chave_acesso = db.Column(db.String(44), unique=True, nullable=False)
    cnpj_destinatario = db.Column(db.String(14), nullable=False)
    nome_destinatario = db.Column(db.String(255), nullable=False)
    cfop = db.Column(db.String(4), nullable=False)
    tipo_operacao = db.Column(db.String(50), nullable=False) # SAIDA, ENTRADA_RETORNO, ENTRADA_DEVOLUCAO, ENTRADA_VENDA
    data_emissao = db.Column(db.DateTime, default=datetime.utcnow)
    xml_content = db.Column(db.Text) # Armazenar o XML completo

    itens = db.relationship('ItemNotaFiscal', backref='nota_fiscal', lazy=True)

    def __repr__(self):
        return f'<NotaFiscal {self.numero_nf} - {self.nome_destinatario}>'

class ItemNotaFiscal(db.Model):
    __tablename__ = 'itens_nota_fiscal'
    id = db.Column(db.Integer, primary_key=True)
    nota_fiscal_id = db.Column(db.Integer, db.ForeignKey('notas_fiscais.id'), nullable=False)
    codigo_produto = db.Column(db.String(50), nullable=False)
    descricao_produto = db.Column(db.String(255), nullable=False)
    numero_lote = db.Column(db.String(50))
    quantidade = db.Column(db.Float, nullable=False)
    valor_unitario = db.Column(db.Float)
    valor_total = db.Column(db.Float)

    def __repr__(self):
        return f'<ItemNF {self.codigo_produto} - {self.quantidade}>'

class EstoqueConsignacao(db.Model):
    __tablename__ = 'estoque_consignacao'
    id = db.Column(db.Integer, primary_key=True)
    codigo_produto = db.Column(db.String(50), nullable=False)
    descricao_produto = db.Column(db.String(255), nullable=False)
    numero_lote = db.Column(db.String(50))
    cnpj_destinatario = db.Column(db.String(14), nullable=False)
    nome_destinatario = db.Column(db.String(255), nullable=False)
    quantidade_enviada = db.Column(db.Float, default=0.0)
    quantidade_retornada = db.Column(db.Float, default=0.0)
    quantidade_faturada = db.Column(db.Float, default=0.0)
    saldo_disponivel = db.Column(db.Float, default=0.0)
    nf_saida_id = db.Column(db.Integer, db.ForeignKey('notas_fiscais.id'))
    nf_entrada_id = db.Column(db.Integer, db.ForeignKey('notas_fiscais.id'))

    def __repr__(self):
        return f'<Estoque {self.codigo_produto} - {self.cnpj_destinatario} - Saldo: {self.saldo_disponivel}>'


