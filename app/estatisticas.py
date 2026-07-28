import plotly.graph_objs as go
import plotly.figure_factory as ff
import plotly.colors as cs
import numpy as np
from app import db

from sqlalchemy import text
from datetime import date, datetime, timedelta


COR_LINHA = '#005E84'
COR_ESCURA = '#002344'
COR_GRADE = '#CCE5F4'
COR_MEDIA = '#8C9BA5'

CAIXA_HOVER = {
    'bgcolor': 'white',
    'bordercolor': COR_GRADE,
    'font': {'family': 'Quicksand, system-ui, sans-serif',
             'size': 13, 'color': COR_ESCURA},
}


def formato_br(valor, casas=0):
    texto = '{:,.{}f}'.format(valor, casas)
    return texto.replace(',', 'X').replace('.', ',').replace('X', '.')


def linha_serie(x, y, hovertemplate):
    return go.Scatter(
        x=x,
        y=y,
        mode='lines+markers',
        line={'color': COR_LINHA, 'width': 2},
        marker={'size': 8},
        hovertemplate=hovertemplate,
    )


def layout_serie_mensal(titulo, titulo_y, media=None, texto_media='',
                        tickformat_y=None):
    eixo_y = {'title': titulo_y, 'rangemode': 'tozero',
              'gridcolor': COR_GRADE, 'linecolor': COR_LINHA}

    if tickformat_y:
        eixo_y['tickformat'] = tickformat_y

    formas = []
    notas = []

    if media is not None:
        formas.append({'type': 'line', 'xref': 'paper', 'x0': 0, 'x1': 1,
                       'yref': 'y', 'y0': media, 'y1': media,
                       'line': {'color': COR_MEDIA, 'width': 1,
                                'dash': 'dash'}})
        notas.append({'xref': 'paper', 'x': 1, 'yref': 'y', 'y': media,
                      'text': texto_media, 'showarrow': False,
                      'xanchor': 'right', 'yanchor': 'bottom',
                      'font': {'size': 11, 'color': COR_MEDIA}})

    return go.Layout(
        template='plotly_white',
        separators=',.',
        height=420,
        margin={'l': 64, 'r': 24, 't': 56, 'b': 48},
        title={'text': titulo, 'x': 0, 'xanchor': 'left',
               'font': {'size': 15, 'color': COR_ESCURA}},
        hovermode='x unified',
        hoverlabel=CAIXA_HOVER,
        xaxis={'title': 'Mês', 'dtick': 'M1', 'tickformat': '%m/%Y',
               'gridcolor': COR_GRADE, 'linecolor': COR_LINHA},
        yaxis=eixo_y,
        shapes=formas,
        annotations=notas,
    )


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

    HAVING COUNT(DISTINCT CONF.pedido) >= 2
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
        marker_color=COR_ESCURA,
        hovertemplate='<b>%{x:.2%}</b> reprovadas<br>%{y}<extra></extra>',
    )

    layout = go.Layout(
        template='plotly_white',
        separators=',.',
        height=420,
        margin={'l': 24, 'r': 24, 't': 56, 'b': 48},
        title={'text': 'Taxa de reprova por fornecedor', 'x': 0,
               'xanchor': 'left',
               'font': {'size': 15, 'color': COR_ESCURA}},
        hovermode='closest',
        hoverlabel=CAIXA_HOVER,
        xaxis={'title': '% de peças reprovadas', 'tickformat': '.1%',
               'gridcolor': COR_GRADE, 'linecolor': COR_LINHA},
        yaxis={'autorange': 'reversed', 'automargin': True,
               'ticksuffix': '  '},
    )

    fig = go.Figure(data=[trace], layout=layout)
    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def lista_fornecedores():

    consulta = text("""SELECT DISTINCT
        TRIM(SA2.A2_NREDUZ) AS FORNECEDOR
    FROM Cotacoes.dbo.RDR_APP_CONFERENCIA CONF

    INNER JOIN Protheus.dbo.SC7010 SC7 ON
        CONF.pedido COLLATE DATABASE_DEFAULT = SC7.C7_NUM AND
        CONF.item   COLLATE DATABASE_DEFAULT = SC7.C7_ITEM

    INNER JOIN Protheus.dbo.SA2010 SA2 ON
        SC7.C7_FORNECE = SA2.A2_COD AND
        SC7.C7_LOJA = SA2.A2_LOJA

    WHERE CONF.ativo = 1 AND
    CONF.pecas_reprovadas > 0 AND
    CONF.dt_hr_inspecao >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) - 11, 0)

    ORDER BY 1""")

    resultado = db.session.execute(consulta).mappings().all()

    return [linha['FORNECEDOR'] for linha in resultado]


def rpncs_por_mes(fornecedor=None):

    filtro_fornecedor = ''
    parametros = {}

    if fornecedor:
        filtro_fornecedor = 'AND TRIM(SA2.A2_NREDUZ) = :var_fornecedor'
        parametros = {'var_fornecedor': fornecedor}

    consulta = text("""SELECT
        DATEFROMPARTS(YEAR(CONF.dt_hr_inspecao), MONTH(CONF.dt_hr_inspecao), 1) AS DT_HR_INSPECAO,
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
    CONF.dt_hr_inspecao >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) - 11, 0)
    """ + filtro_fornecedor + """

    GROUP BY DATEFROMPARTS(YEAR(CONF.dt_hr_inspecao), MONTH(CONF.dt_hr_inspecao), 1)

    ORDER BY 1""")

    resultado = db.session.execute(consulta, parametros).mappings().all()

    data = [linha['DT_HR_INSPECAO'] for linha in resultado]
    pecas = [linha['PECAS_REPROVADAS'] for linha in resultado]

    media = sum(pecas) / len(pecas) if pecas else 0

    if fornecedor:
        titulo = 'Peças reprovadas — {}'.format(fornecedor.title())
    else:
        titulo = 'Peças reprovadas — todos os fornecedores'

    trace = linha_serie(
        data, pecas,
        '<b>%{y:,.0f}</b> peças reprovadas<extra></extra>')

    layout = layout_serie_mensal(
        titulo, 'Peças reprovadas',
        media, 'média {}'.format(formato_br(media)))

    fig = go.Figure(data=[trace], layout=layout)

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def pecas_inspecionadas():

    consulta = text("""SELECT
        DATEFROMPARTS(YEAR(CONF.dt_hr_inspecao), MONTH(CONF.dt_hr_inspecao), 1) AS DT_HR_INSPECAO,
        SUM(CONF.qt_total) AS QT_TOTAL
    FROM Cotacoes.dbo.RDR_APP_CONFERENCIA CONF

    WHERE CONF.ativo = 1 AND
    CONF.dt_hr_inspecao >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) - 11, 0)

    GROUP BY DATEFROMPARTS(YEAR(CONF.dt_hr_inspecao), MONTH(CONF.dt_hr_inspecao), 1)

    ORDER BY 1""")

    resultado = db.session.execute(consulta).mappings().all()

    data = [linha['DT_HR_INSPECAO'] for linha in resultado]
    valores = [linha['QT_TOTAL'] for linha in resultado]

    media = sum(valores) / len(valores) if valores else 0

    trace = linha_serie(
        data, valores,
        '<b>%{y:,.0f}</b> peças inspecionadas<extra></extra>')

    layout = layout_serie_mensal(
        'Peças inspecionadas por mês', 'Peças inspecionadas',
        media, 'média {}'.format(formato_br(media)))

    fig = go.Figure(data=[trace], layout=layout)

    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def taxa_reprova_mensal():
    consulta = text("""SELECT
    CAST(SUM(CONF.pecas_reprovadas) AS DECIMAL(18,4)) 
    / NULLIF(SUM(CONF.qt_total), 0) AS TX_REPROVA
    FROM Cotacoes.dbo.RDR_APP_CONFERENCIA CONF
    WHERE CONF.ativo = 1
    AND CONF.dt_hr_inspecao >= DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)
    AND CONF.dt_hr_inspecao < GETDATE()""")

    tx_reprova = db.session.execute(consulta).scalar()

    if tx_reprova is None:
        return 0.0

    return float(tx_reprova) * 100


def tx_reprova_mes_anterior():
    consulta = text("""SELECT
    CAST(SUM(CONF.pecas_reprovadas) AS DECIMAL(18,4)) 
        / NULLIF(SUM(CONF.qt_total), 0) AS TX_REPROVA
    FROM Cotacoes.dbo.RDR_APP_CONFERENCIA CONF
    WHERE CONF.ativo = 1
    AND CONF.dt_hr_inspecao >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) - 1, 0)
    AND CONF.dt_hr_inspecao <  DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()), 0)""")

    resultado = db.session.execute(consulta).scalar()

    if resultado is None:
        return 0.0

    return float(resultado) * 100


def var_tx_reprova():
    tx_mes = taxa_reprova_mensal()
    tx_mes_passado = tx_reprova_mes_anterior()

    if tx_mes is None or tx_mes_passado is None or tx_mes_passado == 0:
        return 0.0

    return ((tx_mes - tx_mes_passado) / tx_mes_passado)*100


def janela_mes_atual():
    hoje = datetime.now()
    return datetime(hoje.year, hoje.month, 1), hoje


def janela_mes_anterior():
    hoje = datetime.now()
    primeiro_dia_deste_mes = datetime(hoje.year, hoje.month, 1)
    primeiro_dia_do_mes_passado = (
        primeiro_dia_deste_mes - timedelta(days=1)).replace(day=1)
    return primeiro_dia_do_mes_passado, primeiro_dia_deste_mes


def fornecedor_com_mais_reprova(data_de, data_ate):
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

        HAVING COUNT(DISTINCT CONF.pedido) >= 2
        )
        SELECT TOP 1
            FORNECEDOR,
            CAST(PECAS_REPROVADAS AS DECIMAL(18,4)) / NULLIF(QT_TOTAL, 0) AS REPROVA
        FROM FORNECEDOR_PERCENT
        WHERE CAST(PECAS_REPROVADAS AS DECIMAL(18,4)) / NULLIF(QT_TOTAL, 0) > 0
        ORDER BY REPROVA DESC
        """)

    linha = db.session.execute(consulta,
                               {'data_de': data_de,
                                'data_ate': data_ate}
                               ).mappings().first()

    if linha is None:
        return None

    return {'fornecedor': linha['FORNECEDOR'],
            'reprova': float(linha['REPROVA']) * 100}


def contagem_rpncs(de, ate):
    consulta = text("""SELECT
	SUM(CASE WHEN CONF.rpnc IS NULL THEN 0 ELSE 1 END) as RPNC
    FROM Cotacoes.dbo.RDR_APP_CONFERENCIA CONF

    WHERE CONF.ativo = 1 AND
    CONF.dt_hr_inspecao >= :data_de AND
    CONF.dt_hr_inspecao < :data_ate""")

    resultado = db.session.execute(consulta,
                                   {'data_de': de,
                                    'data_ate': ate}).scalar()

    return resultado


def ritmo_conferencias(data_de, data_ate):
    consulta = text("""SELECT
        CAST(COUNT(*) AS DECIMAL(18,4))
        / NULLIF(COUNT(DISTINCT CAST(CONF.dt_hr_inspecao AS DATE)), 0) AS CONF_POR_DIA
    FROM Cotacoes.dbo.RDR_APP_CONFERENCIA CONF
    WHERE CONF.ativo = 1
    AND CONF.dt_hr_inspecao >= :data_de
    AND CONF.dt_hr_inspecao < :data_ate""")

    resultado = db.session.execute(consulta,
                                   {'data_de': data_de,
                                    'data_ate': data_ate}).scalar()

    if resultado is None:
        return 0.0

    return float(resultado)


def taxa_reprova_por_mes():

    consulta = text("""SELECT
        DATEFROMPARTS(YEAR(CONF.dt_hr_inspecao), MONTH(CONF.dt_hr_inspecao), 1) AS MES,
        CAST(SUM(CONF.pecas_reprovadas) AS DECIMAL(18,4))
        / NULLIF(SUM(CONF.qt_total), 0) AS TX_REPROVA
    FROM Cotacoes.dbo.RDR_APP_CONFERENCIA CONF

    WHERE CONF.ativo = 1 AND
    CONF.dt_hr_inspecao >= DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE()) - 11, 0)

    GROUP BY DATEFROMPARTS(YEAR(CONF.dt_hr_inspecao), MONTH(CONF.dt_hr_inspecao), 1)

    ORDER BY 1""")

    resultado = db.session.execute(consulta).mappings().all()

    meses = [linha['MES'] for linha in resultado]
    taxas = [float(linha['TX_REPROVA'] or 0) for linha in resultado]

    media = sum(taxas) / len(taxas) if taxas else 0

    trace = linha_serie(
        meses, taxas,
        '<b>%{y:.2%}</b> das peças reprovadas<extra></extra>')

    layout = layout_serie_mensal(
        'Taxa de reprova por mês', 'Taxa de reprovação',
        media, 'média {}%'.format(formato_br(media * 100, 2)),
        tickformat_y='.1%')

    fig = go.Figure(data=[trace], layout=layout)

    return fig.to_html(full_html=False, include_plotlyjs='cdn')
