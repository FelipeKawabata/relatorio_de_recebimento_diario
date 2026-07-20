from flask import render_template, url_for, request, jsonify, redirect, session, flash
from app import app, db
from app.auth import autenticar_no_protheus, ProtheusIndisponivel, login_obrigatorio
from app.models import Recebimento, Processo, GrupoMaterial, Material, PlanoControle, ListaInstrumentos
from app.metodos import lista_tabela, adicionar_processo, adicionar_grupo_material, adicionar_material
from app.metodos import adicionar_plano_de_controle, adicionar_instrumento
from app.forms import ProcessoForm, GrupoMaterialForm, MaterialForm, PlanoControleForm, ListaInstrumentosForm
from sqlalchemy.exc import IntegrityError


@app.route('/', methods=['GET', 'POST'])
@login_obrigatorio
def homepage():
    if request.method == 'POST':
        pass

    data = '2026-07-14'

    linhas = db.session.scalars(
        db.select(Recebimento)
        .where(Recebimento.dt_emissao == data)
        .order_by(Recebimento.pedido)
        .limit(100)
    ).all()

    return render_template('index.html', linhas=linhas)


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
