from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, DateTime, ForeignKey, Float, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
from app import db


class ListaInstrumentos(db.Model):
    __tablename__ = "RDR_APP_LISTA_INSTRUMENTOS"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(30), nullable=False)
    descricao = db.Column(db.String(70), nullable=True)

    uso_instrumento = relationship(
        'InstrumentoMedicao', back_populates='instrumento')


class InstrumentoMedicao(db.Model):
    __tablename__ = "RDR_APP_INSTRUMENTO_MEDICAO"

    id = db.Column(db.Integer, primary_key=True)
    conferencia_id = db.Column(
        db.Integer, db.ForeignKey('RDR_APP_CONFERENCIA.id'), nullable=False)
    instrumento_id = db.Column(
        db.Integer, db.ForeignKey('RDR_APP_LISTA_INSTRUMENTOS.id'), nullable=False)

    conferencia = db.relationship('Conferencia', back_populates='instrumentos')
    instrumento = db.relationship(
        'ListaInstrumentos', back_populates='uso_instrumento')

    __table_args__ = (
        db.UniqueConstraint('conferencia_id', 'instrumento_id',
                            name='uq_instrumento_por_conferencia'),
    )


class Conferencia(db.Model):
    __tablename__ = "RDR_APP_CONFERENCIA"

    id = db.Column(db.Integer, primary_key=True)
    pedido = db.Column(db.String(6), nullable=False)
    item = db.Column(db.String(4), nullable=False)
    nota_fiscal = db.Column(db.String(9), nullable=False)
    dt_hr_inspecao = db.Column(
        db.DateTime, default=datetime.now, nullable=False)
    corrida = db.Column(db.String(20), nullable=True)
    plano_controle = db.Column(db.String(20), nullable=True)
    analise_certificado = db.Column(db.Boolean, nullable=False)
    analise_visual = db.Column(db.Boolean, nullable=False)
    identif_e_rastreabilidade = db.Column(db.Boolean, nullable=False)
    dimensional = db.Column(db.Boolean, nullable=False)
    dureza_sha = db.Column(db.Boolean, nullable=False)
    dureza_tt = db.Column(db.Boolean, nullable=False)
    ranhura = db.Column(db.Boolean, nullable=False)
    fios18_21 = db.Column(db.Boolean, nullable=False)
    rugosidade_acabamento = db.Column(db.Boolean, nullable=False)
    pecas_aprovadas = db.Column(db.Integer, nullable=False)
    pecas_reprovadas = db.Column(db.Integer, default=0, nullable=False)
    rpnc = db.Column(db.String(10), default=None, nullable=True)
    responsavel = db.Column(db.String(50), nullable=False)

    instrumentos = relationship(
        'InstrumentoMedicao', back_populates='conferencia')

    __table_args__ = (db.UniqueConstraint('pedido', 'item',
                      'nota_fiscal', name='uq_conferencia_pedido_item_nf'),)
