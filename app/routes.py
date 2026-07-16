from flask import render_template, url_for, request, jsonify, redirect, session, flash
from app import app, db
from sqlalchemy import text
from app.auth import autenticar_no_protheus, ProtheusIndisponivel, login_obrigatorio


@app.route('/', methods=['GET', 'POST'])
def homepage():
    if request.method == 'POST':
        pass

    data = request.args.get("data")
    consulta = text("SELECT TOP 100 * FROM dbo.RDR_RECEBIMENTO "
                    "WHERE DT_EMISSAO = :data "
                    "ORDER BY PEDIDO"
                    )
    linhas_consulta = db.session.execute(
        consulta, {"data": data}).mappings().all()

    linhas = [dict(linha) for linha in linhas_consulta]

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
