"""
Carrega conferências REAIS da aba FORM-PR-051 da planilha RO-PR-051 para a
RDR_APP_CONFERENCIA. Diferente do seed_conferencias.py (dados fabricados),
aqui os dados são os históricos digitados no formulário.

Uso — SEMPRE no terminal, nunca pelo Code Runner:

    python carregar_form_pr051.py                   -> simula 50 (padrão)
    python carregar_form_pr051.py --quantos 200     -> simula 200
    python carregar_form_pr051.py --quantos 50 --aplicar  -> grava 50

Mapa das colunas (linha 6 é o cabeçalho; dados começam na 7):
  A data inspeção   E nota fiscal    I plano controle   M..V os 10 checks
  D quantidade      F pedido-item    J material         W aprovadas
  B fornecedor(view)G corrida        K EE (spec)        X reprovadas
  C descrição(view) H certificado    L instrumento(s)   Y RPNC   Z inspetor

Instrumentos: os códigos vêm sujos (IM-0023 vs IM0023). Normalizamos
removendo tudo que não é letra/dígito e MAIÚSCULA (IM-0023 -> IM0023),
criando na RDR_APP_LISTA_INSTRUMENTOS o que faltar.

O login runtime (Relatorio) tem INSERT mas NÃO tem DELETE — para desfazer
é preciso USERBI/DBA (filtrar por responsavel ou pelas datas de inspeção).
"""

import datetime
import re
import sys

import openpyxl

from app import app, db
from app.models import (Recebimento, Conferencia, Corrida, InstrumentoMedicao,
                        Material, PlanoControle, ListaInstrumentos)
from app.metodos import processo_sugerido

APLICAR = "--aplicar" in sys.argv
QUANTOS = 50
if "--quantos" in sys.argv:
    QUANTOS = int(sys.argv[sys.argv.index("--quantos") + 1])

PLANILHA = 'RO-PR-051_Relatório_Diário_de_Recebimento (2026) (novo).xlsx'
ABA = 'FORM-PR-051'

# índices 0-based das colunas
DATA, QTD, NF, PEDIDO, CORRIDA, CERT, PLANO, MAT, EE, INSTR = 0, 3, 4, 5, 6, 7, 8, 9, 10, 11
APROV, REPROV, RPNC, INSPETOR = 22, 23, 24, 25
# os 10 checks, em ordem, mapeados para os atributos do modelo
CHECKS = [
    (12, 'analise_certificado'), (13, 'analise_visual'),
    (14, 'identif_e_rastreabilidade'), (15, 'dimensional'),
    (16, 'dureza_sha'), (17, 'id_ligas'), (18, 'dureza_tt'),
    (19, 'ranhura'), (20, 'fios18_21'), (21, 'rugosidade_acabamento'),
]


def s(v):
    return str(v).strip() if v is not None else ''


def limpo(v):
    """String ou None para placeholders vazios ('-', 'N/A')."""
    t = s(v)
    return None if t in ('', '-', 'N/A', 'n/a') else t


def para_int(v, default=0):
    t = s(v)
    if t in ('', '-', 'N/A'):
        return default
    try:
        return int(float(t))
    except ValueError:
        return default


def para_bool(v):
    t = s(v)
    if t == 'True':
        return True
    if t == 'False':
        return False
    return None   # célula vazia / 'N/A' -> não se aplica


def normalizar_instrumento(codigo):
    """IM-0023 -> IM0023 ; remove tudo que não é letra/dígito, MAIÚSCULA."""
    return re.sub(r'[^A-Za-z0-9]', '', codigo).upper()


with app.app_context():

    materiais_nome = {m.nome.strip(): m for m in db.session.scalars(db.select(Material))}
    materiais_ee = {m.especificacao.strip(): m
                    for m in db.session.scalars(db.select(Material))}
    planos = {p.nome.strip(): p for p in db.session.scalars(db.select(PlanoControle))}
    instrumentos = {i.nome.strip(): i
                    for i in db.session.scalars(db.select(ListaInstrumentos))}

    existentes = set(db.session.execute(db.select(
        Conferencia.pedido, Conferencia.item, Conferencia.nota_fiscal)).all())

    wb = openpyxl.load_workbook(PLANILHA, data_only=True, read_only=True)
    ws = wb[ABA]
    linhas = [r for i, r in enumerate(ws.iter_rows(values_only=True), 1)
              if i >= 7 and isinstance(r[DATA], datetime.datetime)]

    criados = 0
    instr_criados = []
    sem_material = 0
    pulados_dup = 0
    vistos = set()

    for r in linhas:
        if criados == QUANTOS:
            break

        m = re.match(r'^(\d+)\D+(\d+)$', s(r[PEDIDO]))
        if not m:
            continue
        pedido = m.group(1).zfill(6)
        item = m.group(2).zfill(4)
        nf = s(r[NF])
        chave = (pedido, item, nf)

        if chave in existentes or chave in vistos:
            pulados_dup += 1
            continue
        vistos.add(chave)

        qt = para_int(r[QTD])

        # material: por nome, depois por código EE
        material = materiais_nome.get(s(r[MAT])) or materiais_ee.get(s(r[EE]))
        if material is None:
            sem_material += 1

        plano = planos.get(s(r[PLANO]))

        # processo: derivado do produto REAL da view (o form não tem processo)
        recebimento = db.session.get(Recebimento, chave)
        pid = processo_sugerido(recebimento.produto) if recebimento else 0

        conf = Conferencia(
            pedido=pedido, item=item, nota_fiscal=nf,
            dt_hr_inspecao=r[DATA],
            qt_total=qt,
            certificado=(limpo(r[CERT]) or '')[:30] or None,
            plano_controle_id=plano.id if plano else None,
            processo_id=pid or None,
            material_id=material.id if material else None,
            pecas_aprovadas=para_int(r[APROV]),
            pecas_reprovadas=para_int(r[REPROV]),
            rpnc=(limpo(r[RPNC]) or '')[:10] or None,
            responsavel=(s(r[INSPETOR]) or 'IMPORTADO')[:50],
        )
        for idx, atributo in CHECKS:
            setattr(conf, atributo, para_bool(r[idx]))

        # corrida (uma, com a quantidade total)
        corrida_txt = limpo(r[CORRIDA])
        if corrida_txt:
            conf.corridas.append(
                Corrida(corrida=corrida_txt[:50], qtd_corrida=qt))

        # instrumentos: normaliza, cria o que faltar, vincula (sem repetir)
        ids_vinculados = set()
        for bruto in re.split(r'[\/,;]', s(r[INSTR])):
            cod = normalizar_instrumento(bruto)
            if not cod:
                continue
            inst = instrumentos.get(cod)
            if inst is None:
                inst = ListaInstrumentos(nome=cod, descricao=None)
                db.session.add(inst)
                db.session.flush()          # garante o id
                instrumentos[cod] = inst
                instr_criados.append(cod)
            if inst.id not in ids_vinculados:
                conf.instrumentos.append(
                    InstrumentoMedicao(instrumento_id=inst.id))
                ids_vinculados.add(inst.id)

        db.session.add(conf)
        criados += 1

    print(f"Conferências a inserir: {criados}")
    print(f"  sem material resolvido (material_id NULL): {sem_material}")
    print(f"  linhas puladas por chave duplicada: {pulados_dup}")
    print(f"  instrumentos NOVOS criados: "
          f"{sorted(set(instr_criados))} ({len(set(instr_criados))})")

    if APLICAR:
        db.session.commit()
        print("\nGravado.")
    else:
        db.session.rollback()
        print("\nSimulação: nada gravado. Rode com --aplicar para valer.")
