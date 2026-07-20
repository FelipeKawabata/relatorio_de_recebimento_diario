from app import db
from app.models import Processo, ListaInstrumentos, GrupoMaterial, Material, PlanoControle, Recebimento
from flask import flash, redirect, url_for, flash, current_app
from sqlalchemy.exc import IntegrityError
import re
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


# FUNÇÃO GERAL DE LISTAGEM


def lista_tabela(classe):
    return db.session.scalars(db.select(classe)).all()

# FUNÇÕES PARA ADICIONAR RELATÓRIO DE RECEBIMENTO

# Procura o pedido de compra digitiado, verifica formato e verifica se
# tem mais de uma nota fiscal vinculada. A função retorna as linhas que batem
# com o pedido de compra


def procurar_pedido_de_compra(pedido_de_compra):
    match = re.fullmatch(
        r'\s*(?P<pedido>\d{6})[-/\s]+(?P<item>\d{4})\s*',
        pedido_de_compra,
    )
    if not match:
        return None

    pedido, item = match.group('pedido'), match.group('item')

    try:
        linhas = db.session.scalars(
            db.select(Recebimento)
            .where(Recebimento.pedido == pedido, Recebimento.item == item)
            .order_by(Recebimento.nota_fiscal)
            .limit(100)
        ).all()
    except SQLAlchemyError:
        current_app.logger.exception('Falha ao buscar %s/%s', pedido, item)
        return None

    if not linhas:
        return []

    return linhas

# FUNÇÕES PARA ADICIONAR DADOS POR CATEGORIA


def adicionar_processo(nome):
    try:
        db.session.add(Processo(nome=nome))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('Este processo já foi adicionado a lista!')


def adicionar_instrumento(nome, descricao):
    try:
        db.session.add(ListaInstrumentos(nome=nome,
                                         descricao=descricao))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('Este instrumento já foi adicionado a lista!')


def adicionar_grupo_material(nome):
    try:
        db.session.add(GrupoMaterial(nome=nome))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('Este grupo de materiais já foi adicionado a lista!')


def adicionar_material(nome, especificacao, grupo_id_fk):
    try:
        db.session.add(Material(nome=nome,
                                especificacao=especificacao,
                                grupo_id=grupo_id_fk))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('Este material já foi adicionado a lista!')


def adicionar_plano_de_controle(nome, descricao):
    try:
        db.session.add(PlanoControle(nome=nome,
                                     descricao=descricao))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('Este plano de controle já está cadastrado')
