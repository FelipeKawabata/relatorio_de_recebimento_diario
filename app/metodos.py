from app import db
from app.models import Processo, ListaInstrumentos, GrupoMaterial, Material, PlanoControle, Recebimento, Conferencia, Corrida, InstrumentoMedicao
from flask import flash, redirect, url_for, flash, current_app
from sqlalchemy.exc import IntegrityError
import re
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


# FUNÇÃO GERAL DE LISTAGEM


def lista_tabela(classe):
    consulta = db.select(classe)

    if hasattr(classe, 'ativo'):
        consulta = consulta.where(classe.ativo == True)  # noqa: E712 -> ativo = 1
    return db.session.scalars(consulta).all()

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
        pecas_aprovadas=form.pecas_aprovadas.data,
        pecas_reprovadas=form.pecas_reprovadas.data,
        rpnc=form.rpnc.data,
        responsavel=form.responsavel.data,
    )

    # Checkbox que não foi renderizado chega no WTForms como False, e False
    # significa "verifiquei e reprovou" — diferente de NULL, que é "não se
    # aplica". Por isso a regra é recalculada AQUI, no servidor, a partir do
    # material e do processo que estão sendo gravados: o que o cliente mandou
    # não é confiável (o usuário pode ter trocado o material depois que os
    # checkboxes foram desenhados).
    aplicaveis = set(checks_do_form(form))

    for nome in ORDEM_CHECKS:
        setattr(conferencia, nome,
                getattr(form, nome).data if nome in aplicaveis else None)

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


# Cada adicionar_* checa antes se o nome já existe. Isso resolve o conflito
# entre soft delete e a UniqueConstraint(nome): um item desativado continua
# ocupando o nome, então "recadastrar" = reativar a linha antiga (mantendo o
# mesmo id, e portanto o vínculo com as conferências históricas).


def adicionar_processo(nome):
    existente = db.session.scalar(
        db.select(Processo).where(Processo.nome == nome))
    if existente is not None:
        if existente.ativo:
            flash('Este processo já foi adicionado a lista!')
        else:
            existente.ativo = True
            db.session.commit()
            flash('Processo reativado.')
        return
    db.session.add(Processo(nome=nome))
    db.session.commit()


def adicionar_instrumento(nome, descricao):
    existente = db.session.scalar(
        db.select(ListaInstrumentos).where(ListaInstrumentos.nome == nome))
    if existente is not None:
        if existente.ativo:
            flash('Este instrumento já foi adicionado a lista!')
        else:
            existente.ativo = True
            existente.descricao = descricao
            db.session.commit()
            flash('Instrumento reativado.')
        return
    db.session.add(ListaInstrumentos(nome=nome, descricao=descricao))
    db.session.commit()


def adicionar_grupo_material(nome):
    existente = db.session.scalar(
        db.select(GrupoMaterial).where(GrupoMaterial.nome == nome))
    if existente is not None:
        if existente.ativo:
            flash('Este grupo de materiais já foi adicionado a lista!')
        else:
            existente.ativo = True
            db.session.commit()
            flash('Grupo de materiais reativado.')
        return
    db.session.add(GrupoMaterial(nome=nome))
    db.session.commit()


def adicionar_material(nome, especificacao, grupo_id_fk):
    existente = db.session.scalar(
        db.select(Material).where(Material.nome == nome))
    if existente is not None:
        if existente.ativo:
            flash('Este material já foi adicionado a lista!')
        else:
            existente.ativo = True
            existente.especificacao = especificacao
            existente.grupo_id = grupo_id_fk
            db.session.commit()
            flash('Material reativado.')
        return
    db.session.add(Material(nome=nome,
                            especificacao=especificacao,
                            grupo_id=grupo_id_fk))
    db.session.commit()


def adicionar_plano_de_controle(nome, descricao):
    existente = db.session.scalar(
        db.select(PlanoControle).where(PlanoControle.nome == nome))
    if existente is not None:
        if existente.ativo:
            flash('Este plano de controle já está cadastrado')
        else:
            existente.ativo = True
            existente.descricao = descricao
            db.session.commit()
            flash('Plano de controle reativado.')
        return
    db.session.add(PlanoControle(nome=nome, descricao=descricao))
    db.session.commit()

# FUNÇÕES PARA DEFINIDIR QUAL OS CHECKLISTS DEVEM APARECER


def definir_processo(texto: str) -> str:

    # Recebimento.produto é nullable e re.search estoura com None
    if not texto:
        return 'OUT'

    if texto == 'BN1500000000000':
        return 'OUT'

    PADROES = {
        r'^B{1}[A-Z]{1}1[0-1]': 'USI',
        r'^B{1}[A-Z]{1}2[0-2]': 'PNT',
        r'^B{1}[A-Z]{1}2[8-9]': 'REV',
        r'^B{1}[A-Z]{1}3[0-9]': 'REV',
        r'^B{1}[A-Z]{1}50': 'VUL',
        r'^B{1}[A-Z]{1}4[0-1]': 'TT',
        r'^B{1}[A-Z]{1}42': 'REV',
        r'^B{1}[A-Z]{1}5[5-6]': 'POL',
        r'^[^B]{1}.{7}1': 'BRT',
        r'^[^B]{1}.{7}[268]': 'S01',
        r'^[^B]{1}.{7}[4-5]': 'ACB'
    }

    for padrao, resultado in PADROES.items():
        if re.search(padrao, texto):
            return resultado

    return 'OUT'


# Ponte entre a sigla que o regex devolve e o nome cadastrado em RDR_PROCESSO.
# A busca é por NOME, não por id: assim, cadastrar um processo novo pela tela
# de categorias já faz o palpite funcionar, sem mexer em código.
SIGLA_PARA_PROCESSO = {
    'USI': 'Usinagem',
    'PNT': 'Pintura',
    'REV': 'Revestimento',
    'TT':  'Tratamento térmico',
    'POL': 'Polimento',
    'BRT': 'Bruto',
    'S01': 'Semi-acabado',
    'ACB': 'Acabado',
    'VUL': 'Vulcanização',
}


def processo_sugerido(produto: str) -> int:

    nome = SIGLA_PARA_PROCESSO.get(definir_processo(produto))

    if nome is None:
        return 0

    processo = db.session.scalar(
        db.select(Processo).where(Processo.nome == nome))

    return processo.id if processo else 0


ORDEM_CHECKS = ['analise_certificado', 'analise_visual',
                'identif_e_rastreabilidade', 'dimensional',
                'id_ligas', 'dureza_sha', 'dureza_tt',
                'ranhura', 'fios18_21', 'rugosidade_acabamento']

BASE = frozenset({'analise_certificado', 'analise_visual',
                  'identif_e_rastreabilidade', 'dimensional'})
USINAGEM = frozenset({'ranhura', 'fios18_21', 'rugosidade_acabamento'})
LIGA = frozenset({'id_ligas'})
DUREZA_TT = frozenset({'dureza_tt'})
DUREZA_SHA = frozenset({'dureza_sha'})
ACABAMENTO = frozenset({'rugosidade_acabamento'})

REGRAS_CHECKLIST = {

    ('Aço', 'Bruto'):                BASE | LIGA,
    ('Aço', 'Usinagem'):             BASE | LIGA | USINAGEM,
    ('Aço', 'Semi-acabado'):         BASE | LIGA | USINAGEM,
    ('Aço', 'Acabado'):              BASE | LIGA | USINAGEM,
    ('Aço', 'Tratamento térmico'):   BASE | LIGA | DUREZA_TT,
    ('Aço', 'Polimento'):            BASE | LIGA | ACABAMENTO,
    ('Aço', 'Revestimento'):         BASE,
    ('Aço', 'Pintura'):              BASE,


    ('Metais', 'Bruto'):              BASE,
    ('Metais', 'Usinagem'):           BASE | USINAGEM,
    ('Metais', 'Semi-acabado'):       BASE | USINAGEM,
    ('Metais', 'Acabado'):            BASE | USINAGEM,
    ('Metais', 'Tratamento térmico'): BASE | DUREZA_TT,
    ('Metais', 'Polimento'):          BASE | ACABAMENTO,
    ('Metais', 'Revestimento'):       BASE,
    ('Metais', 'Pintura'):            BASE,


    ('Polímeros', 'Bruto'):         BASE | DUREZA_SHA,
    ('Polímeros', 'Vulcanização'):  BASE | DUREZA_SHA,
    ('Polímeros', 'Usinagem'):      BASE | DUREZA_SHA | ACABAMENTO,
    ('Polímeros', 'Semi-acabado'):  BASE | DUREZA_SHA,
    ('Polímeros', 'Acabado'):       BASE | DUREZA_SHA,

    # ---------- Grupos de serviço: o item recebido é o próprio tratamento
    ('Tratamento Térmico', 'Tratamento térmico'):    BASE | DUREZA_TT,
    ('Pintura', 'Pintura'):                          BASE,
    ('Revestimentos e Acabamentos', 'Revestimento'): BASE,
    ('Revestimentos e Acabamentos', 'Polimento'):    BASE | ACABAMENTO,
}


def checks_aplicaveis(grupo_material: str, processo: str) -> frozenset[str]:
    """Conjunto de checks válidos para o par (grupo, processo).

    Aceita None nos dois argumentos (material ou processo ainda não
    escolhido no formulário) e cai no BASE.
    """
    return REGRAS_CHECKLIST.get((grupo_material, processo), BASE)


def checks_ordenados(grupo_material: str, processo: str) -> list[str]:
    """Mesma regra, já na ordem de exibição — é o que o template consome."""
    aplicaveis = checks_aplicaveis(grupo_material, processo)
    return [nome for nome in ORDEM_CHECKS if nome in aplicaveis]


def checks_do_form(form) -> list[str]:
    """Resolve material_id/processo_id do form e devolve os checks da regra.

    É o salto id -> nome que as rotas precisam. Mantém checks_aplicaveis()
    sem contato com o banco, do mesmo jeito que definir_processo().
    """
    material = db.session.get(Material, form.material_id.data or 0)
    processo = db.session.get(Processo, form.processo_id.data or 0)

    return checks_ordenados(
        material.grupo.nome if material and material.grupo else None,
        processo.nome if processo else None,
    )


def validar_regras_checklist() -> dict[str, list[str]]:
    """Confere se as strings usadas em REGRAS_CHECKLIST existem no banco.

    Erro de acento ou de maiúscula não estoura em runtime: a regra
    simplesmente nunca casa e o checklist aparece com o BASE, sem aviso.
    Rode isto depois de editar as regras ou de renomear algo pela tela.
    """
    grupos_banco = {g.nome for g in lista_tabela(GrupoMaterial)}
    processos_banco = {p.nome for p in lista_tabela(Processo)}

    grupos_regra = {chave[0] for chave in REGRAS_CHECKLIST}
    processos_regra = {chave[1] for chave in REGRAS_CHECKLIST}

    colunas = set(Conferencia.__table__.columns.keys())
    checks_regra = {nome for checks in REGRAS_CHECKLIST.values()
                    for nome in checks} | set(ORDEM_CHECKS)

    return {
        'grupos_inexistentes': sorted(grupos_regra - grupos_banco),
        'processos_inexistentes': sorted(processos_regra - processos_banco),
        'checks_inexistentes': sorted(checks_regra - colunas),
        'grupos_sem_regra': sorted(grupos_banco - grupos_regra),
        'processos_sem_regra': sorted(processos_banco - processos_regra),
    }
