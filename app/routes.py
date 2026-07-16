from flask import render_template, url_for, request, jsonify
from app import app, db
from sqlalchemy import text


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
