from flask import render_template, url_for, request, redirect, abort, session, flash, make_response
from app import app, db
from app.auth import autenticar_no_protheus, ProtheusIndisponivel, login_obrigatorio
from app.models import Recebimento, Processo, GrupoMaterial, Material, PlanoControle, ListaInstrumentos, Conferencia
from app.metodos import lista_tabela, adicionar_processo, adicionar_grupo_material, adicionar_material, montar_choices, processo_sugerido
from app.metodos import adicionar_plano_de_controle, adicionar_instrumento, procurar_pedido_de_compra, adicionar_recebimento, checks_do_form
from app.forms import ProcessoForm, GrupoMaterialForm, MaterialForm, PlanoControleForm, ListaInstrumentosForm, ConferenciaForm, InstrumentoMedicaoForm
from sqlalchemy import and_, collate
from sqlalchemy.exc import IntegrityError
from app.metodos_cont import desativar, atualizar_recebimento
import re
from app.estatisticas import porcentagem_rpnc_fornecedor, rpncs_por_mes, pecas_inspecionadas


@app.route('/')
@login_obrigatorio
def homepage():

    fornecedores = db.session.scalars(
        db.select(Recebimento.nome_fornecedor)
        .join(Conferencia, and_(
            collate(Recebimento.pedido,
                    "DATABASE_DEFAULT") == Conferencia.pedido,
            collate(Recebimento.item, "DATABASE_DEFAULT") == Conferencia.item,
            collate(Recebimento.nota_fiscal, "DATABASE_DEFAULT") == Conferencia.nota_fiscal))
        .where(Conferencia.ativo == True)
        .distinct()
        .order_by(Recebimento.nome_fornecedor)
    ).all()

    consulta = (db.select(Conferencia, Recebimento)
                .join(Recebimento, and_(
                    collate(Recebimento.pedido,
                            "DATABASE_DEFAULT") == Conferencia.pedido,
                    collate(Recebimento.item,
                            "DATABASE_DEFAULT") == Conferencia.item,
                    collate(Recebimento.nota_fiscal, "DATABASE_DEFAULT") == Conferencia.nota_fiscal))
                .where(Conferencia.ativo == True))

    pc_item = request.args.get('pc_item', '').strip()
    fornecedor = request.args.get('fornecedor', '').strip()
    data_de = request.args.get('data_de', '').strip()
    data_ate = request.args.get('data_ate', '').strip()

    if data_de:
        consulta = consulta.where(Recebimento.dt_emissao >= data_de)

    if data_ate:
        consulta = consulta.where(Recebimento.dt_emissao <= data_ate)

    if fornecedor:
        consulta = consulta.where(Recebimento.nome_fornecedor == fornecedor)

    if pc_item:
        # aceita "117172" (só pedido) ou "117172-01" (pedido + item). Se o
        # texto não casar o formato, search vira None e o filtro é ignorado
        # em vez de estourar.
        search = re.search(
            r'(?P<pedido>\d{6})(?:[-/\s]+(?P<item>\d{4}))?', pc_item)
        if search:
            consulta = consulta.where(
                Recebimento.pedido == search.group('pedido'))
            if search.group('item'):
                consulta = consulta.where(
                    Recebimento.item == search.group('item'))

    linhas = db.session.execute(consulta).all()

    return render_template('index.html', linhas=linhas, fornecedores=fornecedores)


@app.post('/recebimento/notas')
@login_obrigatorio
def buscar_notas():
    pedido_de_compra = request.form.get('pedido_de_compra', '')

    linhas = procurar_pedido_de_compra(pedido_de_compra)

    if linhas is None:
        return render_template('_lista_nfs.html',
                               erro='Formato inválido. Use o formato ######/####')

    if not linhas:
        return render_template('_lista_nfs.html',
                               erro=f'Nada encontrado para o pedido {pedido_de_compra}')

    return render_template('_lista_nfs.html', linhas=linhas)


@app.post('/recebimento/conferencia')
@login_obrigatorio
def escolher_nota():
    linha = db.session.get(Recebimento, (request.form.get('pedido'),
                                         request.form.get('item'),
                                         request.form.get('nota_fiscal')))

    if linha is None:
        return '<p class="text-danger">Recebimento não encontrado.</p>'

    form = ConferenciaForm(formdata=None,
                           pedido=linha.pedido,
                           item=linha.item,
                           nota_fiscal=linha.nota_fiscal,
                           qt_total=int(linha.quantidade),
                           processo_id=processo_sugerido(linha.produto))
    montar_choices(form)

    resposta = make_response(render_template('_form_recebimento.html',
                                             form=form, linha=linha,
                                             checks=checks_do_form(form)))
    resposta.headers['HX-Trigger-After-Swap'] = 'abrirModalConferencia'
    return resposta


@app.post('/recebimento')
@login_obrigatorio
def gravar_recebimento():

    dados = request.form.copy()

    if not dados.get('houve_nao_conformidade'):
        dados['pecas_reprovadas'] = '0'
        dados['pecas_aprovadas'] = dados.get('qt_total', '')
        dados['rpnc'] = ''

    form = ConferenciaForm(formdata=dados)
    montar_choices(form)

    if form.validate_on_submit() and adicionar_recebimento(form):
        resposta = make_response('')
        resposta.headers['HX-Trigger'] = 'recebimentoGravado'
        return resposta

    linha = db.session.get(Recebimento, (form.pedido.data,
                                         form.item.data,
                                         form.nota_fiscal.data))

    return render_template('_form_recebimento.html', form=form, linha=linha,
                           checks=checks_do_form(form))


@app.post('/recebimento/corridas')
@login_obrigatorio
def nova_linha_corrida():
    form = ConferenciaForm()
    form.corridas.append_entry()
    return render_template('_corridas.html', form=form)


@app.post('/recebimento/instrumentos')
@login_obrigatorio
def nova_linha_instrumento():
    form = ConferenciaForm()
    form.instrumentos.append_entry()
    montar_choices(form)
    return render_template('_instrumentos.html', form=form)


@app.post('/recebimento/checklist')
@login_obrigatorio
def checklist():
    form = ConferenciaForm()
    montar_choices(form)

    return render_template('_checklist.html', form=form,
                           checks=checks_do_form(form))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            usuario = autenticar_no_protheus(
                request.form["usuario"], request.form["senha"])
        except ProtheusIndisponivel:
            flash("Protheus indisponível no momento. Tente de novo em instantes.")
            return render_template("login.html")
        if usuario:
            session["usuario"] = usuario["user_name"]
            session.permanent = "manter_conectado" in request.form
            return redirect(url_for("homepage"))
        flash("Usuário ou senha inválidos.")
    return render_template("login.html")


@app.get("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login"))


@app.route("/categorias", methods=['GET', 'POST'])
@login_obrigatorio
def categorias():

    # CRIAÇÃO DE CADA FORMULÁRIO

    form_processo = ProcessoForm()
    form_grupo_material = GrupoMaterialForm()
    form_material = MaterialForm()
    form_plano_de_controle = PlanoControleForm()
    form_instrumentos = ListaInstrumentosForm()

    # POPULAÇÃO DOS CAMPOS SELECT

    form_material.grupo_id.choices = [
        (g.id, g.nome) for g in lista_tabela(GrupoMaterial)]

    # ORGANIZAÇÃO DE CADA UM DOS METODOS POST

    if form_processo.enviar_processo.data and form_processo.validate_on_submit():
        adicionar_processo(form_processo.nome.data)
        flash('Processo adicionado com sucesso!')
        return redirect(url_for('categorias'))

    elif (form_grupo_material.enviar_grupo_material.data
          and form_grupo_material.validate_on_submit()):
        adicionar_grupo_material(form_grupo_material.nome.data)
        flash('Grupo de material adicionado com sucesso')
        return redirect(url_for('categorias'))

    elif form_material.enviar_material.data and form_material.validate_on_submit():
        adicionar_material(form_material.nome.data,
                           form_material.especificacao.data,
                           form_material.grupo_id.data)
        flash('Material adicionado com sucesso')
        return redirect(url_for('categorias'))

    elif form_plano_de_controle.enviar_plano_controle.data and form_plano_de_controle.validate_on_submit():
        adicionar_plano_de_controle(form_plano_de_controle.nome.data,
                                    form_plano_de_controle.descricao.data)
        flash('Plano de controle adicionado com sucesso')
        return redirect(url_for('categorias'))

    elif form_instrumentos.enviar_instrumento.data and form_instrumentos.validate_on_submit():
        adicionar_instrumento(form_instrumentos.nome.data,
                              form_instrumentos.descricao.data)
        flash('Instrumento adicionado com sucesso')
        return redirect(url_for('categorias'))

    # LINHAS PARA PREENCHIMENTO DE TABELA

    linhas_processo = lista_tabela(Processo)
    linhas_gp_material = lista_tabela(GrupoMaterial)
    linhas_material = (
        db.session.query(Material, GrupoMaterial)
        .outerjoin(GrupoMaterial, Material.grupo_id == GrupoMaterial.id)
        .filter(Material.ativo == True)
        .order_by(Material.grupo_id, Material.nome)
        .all()
    )
    linhas_plano_de_controle = lista_tabela(PlanoControle)
    linhas_instrumentos = lista_tabela(ListaInstrumentos)

    return render_template("categorias.html",
                           # POST
                           form_processo=form_processo,
                           form_grupo_material=form_grupo_material,
                           form_material=form_material,
                           form_plano_de_controle=form_plano_de_controle,
                           form_instrumentos=form_instrumentos,
                           # GET
                           linhas_processo=linhas_processo,
                           linhas_gp_material=linhas_gp_material,
                           linhas_material=linhas_material,
                           linhas_plano_de_controle=linhas_plano_de_controle,
                           linhas_instrumentos=linhas_instrumentos
                           )


@app.post('/categorias/<tipo>/<int:id>/desativar')
@login_obrigatorio
def desativar_categoria(tipo, id):
    classes = {'processo': Processo, 'grupo': GrupoMaterial,
               'material': Material, 'plano': PlanoControle,
               'instrumento': ListaInstrumentos}
    classe = classes.get(tipo)
    if classe is None:
        abort(404)
    desativar(classe, id)
    return redirect(url_for('categorias'))


CATEGORIAS = {
    'processo':    (Processo,          ProcessoForm),
    'grupo':       (GrupoMaterial,     GrupoMaterialForm),
    'material':    (Material,          MaterialForm),
    'plano':       (PlanoControle,     PlanoControleForm),
    'instrumento': (ListaInstrumentos, ListaInstrumentosForm),
}


@app.route('/categorias/<tipo>/<int:id>/editar', methods=['GET', 'POST'])
@login_obrigatorio
def editar_categoria(tipo, id):
    par = CATEGORIAS.get(tipo)
    if par is None:
        abort(404)
    Modelo, FormClasse = par
    obj = db.session.get(Modelo, id)
    if obj is None:
        abort(404)

    form = FormClasse(obj=obj)
    if tipo == 'material':
        form.grupo_id.choices = [(g.id, g.nome)
                                 for g in lista_tabela(GrupoMaterial)]

    if form.validate_on_submit():

        for campo in form:
            if campo.type not in ('SubmitField', 'CSRFTokenField'):
                setattr(obj, campo.name, campo.data)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            form.nome.errors.append('Já existe outro registro com esse nome.')
            return render_template('_editar_categoria.html', form=form, tipo=tipo, id=id)

        resposta = make_response('')
        resposta.headers['HX-Trigger'] = 'categoriaEditada'
        return resposta

    return render_template('_editar_categoria.html', form=form, tipo=tipo, id=id)


@app.route('/recebimento/<int:id>/editar', methods=['GET', 'POST'])
@login_obrigatorio
def editar_recebimento(id):
    conferencia = db.session.get(Conferencia, id)
    if conferencia is None:
        abort(404)

    if request.method == 'POST':

        dados = request.form.copy()
        if not dados.get('houve_nao_conformidade'):
            dados['pecas_reprovadas'] = '0'
            dados['pecas_aprovadas'] = dados.get('qt_total', '')
            dados['rpnc'] = ''
        form = ConferenciaForm(formdata=dados)
    else:
        form = ConferenciaForm(obj=conferencia)

        form.houve_nao_conformidade.data = (
            bool(conferencia.pecas_reprovadas) or bool(conferencia.rpnc))

    montar_choices(form)

    if form.validate_on_submit() and atualizar_recebimento(conferencia, form):
        resposta = make_response('')
        resposta.headers['HX-Trigger'] = 'recebimentoEditado'
        return resposta

    linha = db.session.get(Recebimento, (conferencia.pedido,
                                         conferencia.item,
                                         conferencia.nota_fiscal))
    return render_template('_editar_deletar_recebimento.html',
                           form=form, conferencia=conferencia,
                           linha=linha, checks=checks_do_form(form))


@app.post('/recebimento/<int:id>/desativar')
@login_obrigatorio
def desativar_recebimento(id):
    desativar(Conferencia, id)
    resposta = make_response('')
    resposta.headers['HX-Trigger'] = 'recebimentoEditado'
    return resposta


@app.route('/estatisticas', methods=['GET'])
@login_obrigatorio
def estatistica():

    data_de = request.args.get('data_de', '').strip() or None
    data_ate = request.args.get('data_ate', '').strip() or None
    fornecedor = request.args.get('fornecedor', '').strip() or None

    graf_pecas_inpecionadas = pecas_inspecionadas()
    graf_rpnc_mes = rpncs_por_mes(fornecedor)
    graf_percent_rpnc = porcentagem_rpnc_fornecedor(data_de, data_ate)

    graficos = {
        'graf_pecas_inpecionadas': graf_pecas_inpecionadas,
        'graf_rpnc_mes': graf_rpnc_mes,
        'graf_percent_rpnc': graf_percent_rpnc
    }

    return render_template('estatisticas.html', graficos=graficos)
