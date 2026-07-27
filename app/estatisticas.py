import plotly.graph_objs as go
import plotly.figure_factory as ff
import plotly.colors as cs
import numpy as np
from app import db

from sqlalchemy import text
from datetime import date, datetime, timedelta


def porcentagem_rpnc_fornecedor(var_data_de=None, var_data_ate=None):

    try:
        data_de = datetime.strptime(var_data_de, '%Y-%m-%d')
    except (TypeError, ValueError):
        data_de = datetime.now() - timedelta(days=10*365)

    try:
        data_ate = datetime.strptime(var_data_ate, '%Y-%m-%d')
        data_ate = data_ate + timedelta(days=1)
    except (TypeError, ValueError):
        data_ate = datetime.now() + timedelta(days=1)

    consulta = text(
        """
    WITH FORNECEDOR_PERCENT AS (
    SELECT
        TRIM(SA2.A2_NREDUZ) AS FORNECEDOR,
        SUM(CONF.pecas_reprovadas) AS PECAS_REPROVADAS,
        SUM(CONF.qt_total) AS QT_TOTAL
    FROM Cotacoes.dbo.RDR_APP_CONFERENCIA CONF

    INNER JOIN Protheus.dbo.SC7010 SC7 ON
        CONF.pedido COLLATE DATABASE_DEFAULT = SC7.C7_NUM AND
        CONF.item   COLLATE DATABASE_DEFAULT = SC7.C7_ITEM

    INNER JOIN Protheus.dbo.SA2010 SA2 ON
        SC7.C7_FORNECE = SA2.A2_COD AND
        SC7.C7_LOJA = SA2.A2_LOJA

    WHERE CONF.ativo = 1 AND
    CONF.dt_hr_inspecao >= :data_de AND
    CONF.dt_hr_inspecao < :data_ate

    GROUP BY TRIM(SA2.A2_NREDUZ)
    )

    SELECT 
        FORNECEDOR,
        CAST(PECAS_REPROVADAS AS DECIMAL(18,4)) / NULLIF(QT_TOTAL, 0) AS REPROVA
    FROM FORNECEDOR_PERCENT
    
        WHERE CAST(PECAS_REPROVADAS AS DECIMAL(18,4)) / NULLIF(QT_TOTAL, 0) > 0
    
        ORDER BY REPROVA DESC
    """)

    resultado = db.session.execute(consulta,
                                   {'data_de': data_de,
                                    'data_ate': data_ate}
                                   ).mappings().all()

    fornecedores = [linha['FORNECEDOR'] for linha in resultado]
    valores = [linha['REPROVA'] for linha in resultado]

    trace = go.Bar(
        x=valores,
        y=fornecedores,
        orientation='h',
        marker_color='#002344',
        hovertemplate='<b>%{x:.1%}</b> reprovadas<br>%{y}<extra></extra>',
    )

    layout = go.Layout(
        template='plotly_white',
        separators=',.',
        height=520,
        margin={'l': 8, 'r': 16, 't': 32, 'b': 8},
        xaxis={'title': '% de peças reprovadas', 'tickformat': '.0%',
               'gridcolor': '#CCE5F4'},
        yaxis={'autorange': 'reversed', 'automargin': True, 'ticksuffix': '  '},
    )

    fig = go.Figure(data=[trace], layout=layout)
    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def rpncs_por_mes(fornecedor=None):

    fornecedor = fornecedor or 'MS USINAGEM MAX'

    consulta = text("""SELECT
        DATEFROMPARTS(YEAR(CONF.dt_hr_inspecao), MONTH(CONF.dt_hr_inspecao), 1) AS DT_HR_INSPECAO,
        TRIM(SA2.A2_NREDUZ) AS FORNECEDOR,
        SUM(CONF.pecas_reprovadas) AS PECAS_REPROVADAS
    FROM Cotacoes.dbo.RDR_APP_CONFERENCIA CONF

    INNER JOIN Protheus.dbo.SC7010 SC7 ON
        CONF.pedido COLLATE DATABASE_DEFAULT = SC7.C7_NUM AND
        CONF.item   COLLATE DATABASE_DEFAULT = SC7.C7_ITEM

    INNER JOIN Protheus.dbo.SA2010 SA2 ON
        SC7.C7_FORNECE = SA2.A2_COD AND
        SC7.C7_LOJA = SA2.A2_LOJA

    WHERE CONF.ativo = 1 AND
    CONF.pecas_reprovadas > 0 AND
    CONF.dt_hr_inspecao >= DATEADD(YEAR, -1, GETDATE()) AND
    TRIM(SA2.A2_NREDUZ) = :var_fornecedor

    GROUP BY DATEFROMPARTS(YEAR(CONF.dt_hr_inspecao), MONTH(CONF.dt_hr_inspecao), 1),
      TRIM(SA2.A2_NREDUZ)

    ORDER BY 1""")

    resultado = db.session.execute(
        consulta, {'var_fornecedor': fornecedor}).mappings().all()

    data = [linha['DT_HR_INSPECAO'] for linha in resultado]
    pecas = [linha['PECAS_REPROVADAS'] for linha in resultado]

    trace = go.Scatter(
        x=data,
        y=pecas,
        mode='lines',
        line={'color': '#005E84', 'width': 2}
    )

    layout = go.Layout(
        template='plotly_white',
        separators=',.',
        hovermode='x unified',
        hoverlabel={
            'bgcolor': 'white',
            'bordercolor': '#CCE5F4',
            'font': {'family': 'Quicksand, system-ui, sans-serif',
                     'size': 13, 'color': '#002344'},
        },
        xaxis={'title': 'Mês', 'dtick': 'M1', 'tickformat': '%m/%Y',
               'gridcolor': '#CCE5F4', 'linecolor': '#005E84'},
        yaxis={'title': 'Peças reprovadas',
               'gridcolor': '#CCE5F4', 'linecolor': '#005E84'},
    )

    fig = go.Figure(data=[trace], layout=layout)

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def pecas_inspecionadas():

    consulta = text("""SELECT
        DATEFROMPARTS(YEAR(CONF.dt_hr_inspecao), MONTH(CONF.dt_hr_inspecao), 1) AS DT_HR_INSPECAO,
        SUM(CONF.qt_total) AS QT_TOTAL
    FROM Cotacoes.dbo.RDR_APP_CONFERENCIA CONF

    WHERE CONF.ativo = 1 AND
    CONF.dt_hr_inspecao >= DATEADD(YEAR, -1, GETDATE())

    GROUP BY DATEFROMPARTS(YEAR(CONF.dt_hr_inspecao), MONTH(CONF.dt_hr_inspecao), 1)

    ORDER BY 1""")

    resultado = db.session.execute(consulta).mappings().all()

    data = [linha['DT_HR_INSPECAO'] for linha in resultado]
    valores = [linha['QT_TOTAL'] for linha in resultado]

    trace = go.Scatter(
        x=data,
        y=valores,
        mode='lines',
        line={'color': '#005E84', 'width': 2}
    )

    layout = go.Layout(
        template='plotly_white',
        separators=',.',
        hovermode='x unified',
        hoverlabel={
            'bgcolor': 'white',
            'bordercolor': '#CCE5F4',
            'font': {'family': 'Quicksand, system-ui, sans-serif',
                     'size': 13, 'color': '#002344'},
        },
        xaxis={'title': 'Mês', 'dtick': 'M1', 'tickformat': '%m/%Y',
               'gridcolor': '#CCE5F4', 'linecolor': '#005E84'},
        yaxis={'title': 'Peças inspecionadas',
               'gridcolor': '#CCE5F4', 'linecolor': '#005E84'},
    )

    fig = go.Figure(data=[trace], layout=layout)

    return fig.to_html(full_html=False, include_plotlyjs='cdn')
