from app import db
from flask import flash, current_app
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models import Corrida, InstrumentoMedicao
from app.metodos import checks_do_form, ORDEM_CHECKS


def desativar(classe, id):
    obj = db.session.get(classe, id)

    if obj is None:
        flash('Registro não encontrado')
        return

    obj.ativo = False
    db.session.commit()

    flash('Registro desativado')

# EDIÇÃO DO FORM RECEBIMENTO


def atualizar_recebimento(conferencia, form):

    conferencia.qt_total = form.qt_total.data
    conferencia.certificado = form.certificado.data
    conferencia.plano_controle_id = form.plano_controle_id.data or None
    conferencia.processo_id = form.processo_id.data or None
    conferencia.material_id = form.material_id.data or None
    conferencia.pecas_aprovadas = form.pecas_aprovadas.data
    conferencia.pecas_reprovadas = form.pecas_reprovadas.data
    conferencia.rpnc = form.rpnc.data
    conferencia.responsavel = form.responsavel.data

    aplicaveis = set(checks_do_form(form))
    for nome in ORDEM_CHECKS:
        setattr(conferencia, nome,
                getattr(form, nome).data if nome in aplicaveis else None)

    try:
        # Replace de corridas e instrumentos: esvazia a relação e recria a
        # partir do form. O cascade='all, delete-orphan' faz o SQLAlchemy
        # APAGAR as linhas que saíram (precisa de DELETE em RDR_CORRIDA /
        # RDR_APP_INSTRUMENTO_MEDICAO). O flush() força os DELETEs a saírem
        # ANTES dos INSERTs — senão, ao reusar o mesmo instrumento, a
        # UniqueConstraint (conferencia_id, instrumento_id) colidiria.
        conferencia.corridas.clear()
        conferencia.instrumentos.clear()
        db.session.flush()

        for entrada in form.corridas:
            conferencia.corridas.append(
                Corrida(corrida=entrada.corrida.data,
                        qtd_corrida=entrada.qtd_corrida.data))

        for entrada in form.instrumentos:
            conferencia.instrumentos.append(
                InstrumentoMedicao(instrumento_id=entrada.instrumento_id.data))

        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        flash('Já existe uma conferência para este pedido/item/nota fiscal.')
        return False
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception('Falha ao atualizar %s', conferencia.id)
        flash('Erro ao atualizar o recebimento. Tente novamente.')
        return False
