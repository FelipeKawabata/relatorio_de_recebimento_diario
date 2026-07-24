from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app import db


class ListaInstrumentos(db.Model):
    __tablename__ = "RDR_APP_LISTA_INSTRUMENTOS"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(30), nullable=False)
    descricao = db.Column(db.String(70), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    uso_instrumento = relationship(
        'InstrumentoMedicao', back_populates='instrumento')

    __table_args__ = (
        db.UniqueConstraint('nome', name='uq_nome_instrumento'),)


class InstrumentoMedicao(db.Model):
    __tablename__ = "RDR_APP_INSTRUMENTO_MEDICAO"

    id = db.Column(db.Integer, primary_key=True)
    conferencia_id = db.Column(
        db.Integer, db.ForeignKey('RDR_APP_CONFERENCIA.id'), nullable=False)
    instrumento_id = db.Column(
        db.Integer, db.ForeignKey('RDR_APP_LISTA_INSTRUMENTOS.id'), nullable=False)

    conferencia = relationship('Conferencia', back_populates='instrumentos')
    instrumento = relationship(
        'ListaInstrumentos', back_populates='uso_instrumento')

    __table_args__ = (
        db.UniqueConstraint('conferencia_id', 'instrumento_id',
                            name='uq_instrumento_por_conferencia'),)


class GrupoMaterial(db.Model):
    __tablename__ = "RDR_GRUPO_MATERIAL"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)

    grupo_origem = relationship('Material', back_populates='grupo')
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    __table_args__ = (db.UniqueConstraint(
        'nome', name='uq_nome_grupo_material'),)


class Material(db.Model):
    __tablename__ = "RDR_MATERIAL"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(40), nullable=False)
    especificacao = db.Column(db.String(40), nullable=False)
    grupo_id = db.Column(db.Integer, ForeignKey(
        'RDR_GRUPO_MATERIAL.id'), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    origem_material = relationship('Conferencia', back_populates='material')

    grupo = relationship('GrupoMaterial', back_populates='grupo_origem')

    __table_args__ = (db.UniqueConstraint('nome', name='uq_nome_material'),)


class Corrida(db.Model):
    __tablename__ = "RDR_CORRIDA"

    id = db.Column(db.Integer, primary_key=True)
    corrida = db.Column(db.String(50), nullable=False)
    qtd_corrida = db.Column(db.Integer, nullable=False)
    conferencia_id = db.Column(
        db.Integer, ForeignKey('RDR_APP_CONFERENCIA.id'))

    conferencia = relationship(
        'Conferencia', back_populates='corridas')


class Processo(db.Model):
    __tablename__ = "RDR_PROCESSO"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    origem_processo = relationship('Conferencia', back_populates='processo')

    __table_args__ = (db.UniqueConstraint('nome', name='uq_nome_processo'),)


class Conferencia(db.Model):
    __tablename__ = "RDR_APP_CONFERENCIA"

    id = db.Column(db.Integer, primary_key=True)
    pedido = db.Column(db.String(6), nullable=False)
    item = db.Column(db.String(4), nullable=False)
    nota_fiscal = db.Column(db.String(9), nullable=False)
    dt_hr_inspecao = db.Column(
        db.DateTime, default=datetime.now, nullable=False)
    qt_total = db.Column(db.Integer, nullable=False)
    certificado = db.Column(db.String(30), nullable=True)
    plano_controle_id = db.Column(
        db.Integer, ForeignKey('RDR_PLANO_CONTROLE.id'))
    processo_id = db.Column(db.Integer, ForeignKey('RDR_PROCESSO.id'))
    material_id = db.Column(db.Integer, ForeignKey('RDR_MATERIAL.id'))
    analise_certificado = db.Column(db.Boolean, nullable=True)
    analise_visual = db.Column(db.Boolean, nullable=True)
    identif_e_rastreabilidade = db.Column(db.Boolean, nullable=True)
    dimensional = db.Column(db.Boolean, nullable=True)
    dureza_sha = db.Column(db.Boolean, nullable=True)
    id_ligas = db.Column(db.Boolean, nullable=True)
    dureza_tt = db.Column(db.Boolean, nullable=True)
    ranhura = db.Column(db.Boolean, nullable=True)
    fios18_21 = db.Column(db.Boolean, nullable=True)
    rugosidade_acabamento = db.Column(db.Boolean, nullable=True)
    pecas_aprovadas = db.Column(db.Integer, nullable=False)
    pecas_reprovadas = db.Column(db.Integer, default=0, nullable=False)
    rpnc = db.Column(db.String(10), default=None, nullable=True)
    responsavel = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    instrumentos = relationship(
        'InstrumentoMedicao', back_populates='conferencia',
        cascade='all, delete-orphan')
    plano_controle = relationship(
        'PlanoControle', back_populates='origem_plano_controle')
    material = relationship(
        'Material', back_populates='origem_material')
    corridas = relationship('Corrida', back_populates='conferencia',
                            cascade='all, delete-orphan')
    processo = relationship('Processo', back_populates='origem_processo')

    __table_args__ = (db.UniqueConstraint('pedido', 'item',
                      'nota_fiscal', name='uq_conferencia_pedido_item_nf'),)


class PlanoControle(db.Model):
    __tablename__ = "RDR_PLANO_CONTROLE"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(30), nullable=False)
    descricao = db.Column(db.String(50))
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    origem_plano_controle = relationship(
        'Conferencia', back_populates='plano_controle')

    __table_args__ = (
        db.UniqueConstraint('nome', name='uq_nome_plano_de_controle'),)


class Recebimento(db.Model):
    __tablename__ = "RDR_RECEBIMENTO"
    __table_args__ = {"schema": "Protheus.dbo"}

    pedido = db.Column("PEDIDO", db.String(6), primary_key=True)
    item = db.Column("ITEM", db.String(4), primary_key=True)
    nota_fiscal = db.Column("NOTA_FISCAL", db.String(9), primary_key=True)
    produto = db.Column("PRODUTO", db.String(20))
    descricao = db.Column("DESCRICAO", db.String(100))
    quantidade = db.Column("QUANTIDADE", db.Numeric(12, 2))
    nome_fornecedor = db.Column("NOME_FORNECEDOR", db.String(100))
    cod_fornecedor = db.Column("COD_FORNECEDOR", db.String(6))
    loja_fornecedor = db.Column("LOJA_FORNECEDOR", db.String(2))
    dt_emissao = db.Column("DT_EMISSAO", db.Date)
    emissao_nf = db.Column("EMISSAO_NF", db.Date)
    b1_iaespec = db.Column("B1_IAESPEC", db.String(50))
