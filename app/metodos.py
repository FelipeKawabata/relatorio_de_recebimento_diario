from app import db
from app.models import Processo, ListaInstrumentos, GrupoMaterial, Material, PlanoControle, Recebimento, Conferencia, Corrida, InstrumentoMedicao
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


def adicionar_recebimento(form):
    conferencia = Conferencia(
        pedido=form.pedido.data,
        item=form.item.data,
        nota_fiscal=form.nota_fiscal.data,
        qt_total=form.qt_total.data,
        certificado=form.certificado.data,
        plano_controle_id=form.plano_controle_id.data or None,
        processo_id=form.processo_id.data or None,
        material_id=form.material_id.data or None,
        analise_certificado=form.analise_certificado.data,
        analise_visual=form.analise_visual.data,
        identif_e_rastreabilidade=form.identif_e_rastreabilidade.data,
        dimensional=form.dimensional.data,
        dureza_sha=form.dureza_sha.data,
        id_ligas=form.id_ligas.data,
        dureza_tt=form.dureza_tt.data,
        ranhura=form.ranhura.data,
        fios18_21=form.fios18_21.data,
        rugosidade_acabamento=form.rugosidade_acabamento.data,
        pecas_aprovadas=form.pecas_aprovadas.data,
        pecas_reprovadas=form.pecas_reprovadas.data,
        rpnc=form.rpnc.data,
        responsavel=form.responsavel.data,
    )

    for entrada in form.corridas:
        conferencia.corridas.append(
            Corrida(corrida=entrada.corrida.data,
                    qtd_corrida=entrada.qtd_corrida.data))

    for entrada in form.instrumentos:
        conferencia.instrumentos.append(
            InstrumentoMedicao(instrumento_id=entrada.instrumento_id.data))

    try:
        db.session.add(conferencia)
        db.session.commit()
        return True

    except IntegrityError:
        db.session.rollback()
        flash('Já existe uma conferência para este pedido/item/nota fiscal.')
        return False

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            'Falha ao gravar conferência %s/%s/%s',
            form.pedido.data, form.item.data, form.nota_fiscal.data)
        flash('Erro ao gravar o recebimento. Tente novamente.')
        return False


def montar_choices(form):
    form.processo_id.choices = [(0, '— selecione —')] + \
        [(p.id, p.nome) for p in lista_tabela(Processo)]
    form.material_id.choices = [(0, '— selecione —')] + \
        [(m.id, m.nome) for m in lista_tabela(Material)]
    form.plano_controle_id.choices = [(0, '— selecione —')] + \
        [(p.id, p.nome) for p in lista_tabela(PlanoControle)]

    instrumentos = [(i.id, i.nome) for i in lista_tabela(ListaInstrumentos)]
    for entrada in form.instrumentos:
        entrada.instrumento_id.choices = instrumentos


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
