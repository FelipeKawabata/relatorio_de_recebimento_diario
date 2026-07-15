from flask import render_template, url_for, request, jsonify
from app import app, db
from sqlalchemy import text


@app.route('/', methods=['GET', 'POST'])
def homepage():

    return render_template('index.html')


@app.get('/recebimentos/')
def recebimentos():
        data = request.args.get("data")
    consulta = text(
        "SELECT TOP 100 * FROM dbo.RDR_RECEBIMENTO "
        "WHERE DT_EMISSAO = :data "
        "ORDER BY PEDIDO"
    )
    linhas = db.session.execute(consulta, {"data": data}).mappings().all()
