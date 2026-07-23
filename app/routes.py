from flask import render_template, url_for, request, redirect, session, flash, make_response
from app import app, db
from app.auth import autenticar_no_protheus, ProtheusIndisponivel, login_obrigatorio
from app.models import Recebimento, Processo, GrupoMaterial, Material, PlanoControle, ListaInstrumentos, Conferencia
from app.metodos import lista_tabela, adicionar_processo, adicionar_grupo_material, adicionar_material, montar_choices, processo_sugerido
from app.metodos import adicionar_plano_de_controle, adicionar_instrumento, procurar_pedido_de_compra, adicionar_recebimento, checks_do_form
from app.forms import ProcessoForm, GrupoMaterialForm, MaterialForm, PlanoControleForm, ListaInstrumentosForm, ConferenciaForm, InstrumentoMedicaoForm
from sqlalchemy import and_, collate


@app.route('/')
@login_obrigatorio
def homepage():

    linhas = db.session.execute(
        db.select(Conferencia, Recebimento).join(Recebimento, and_(
            collate(Recebimento.pedido,
                    "DATABASE_DEFAULT") == Conferencia.pedido,
            collate(Recebimento.item, "DATABASE_DEFAULT") == Conferencia.item,
            collate(Recebimento.nota_fiscal, "DATABASE_DEFAULT") == Conferencia.nota_fiscal)))

    return render_template('index.html', linhas=linhas)


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

    # request.form é imutável; a cópia é o que permite preencher os campos
    # que ficaram escondidos no collapse. O form PRECISA ler daqui — sem o
    # formdata=dados ele volta a ler o request.form original e o ajuste
    # abaixo não tem efeito nenhum.
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
    linhas_material = lista_tabela(Material)
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
