"""
Cria conferências de TESTE ligadas a recebimentos reais da view, para
desenvolver o index.html. Todas marcadas com responsavel='SEED-TESTE'.

Uso — SEMPRE no terminal, nunca pelo Code Runner:

    python seed_conferencias.py                      -> simula 10 (padrão)
    python seed_conferencias.py --quantos 50         -> simula 50
    python seed_conferencias.py --quantos 50 --aplicar   -> grava 50

Sem --aplicar termina em rollback(), então dá para simular à vontade.
Acumula por cima do que já existe: nunca reusa uma chave (pedido/item/nf)
que já tenha conferência, então pode rodar várias cargas.

ATENÇÃO: o login de runtime (Relatorio) tem INSERT mas NÃO tem DELETE.
Para remover estes dados depois é preciso o login DDL (USERBI) ou o DBA:
    DELETE FROM RDR_APP_INSTRUMENTO_MEDICAO WHERE conferencia_id IN
        (SELECT id FROM RDR_APP_CONFERENCIA WHERE responsavel='SEED-TESTE');
    DELETE FROM RDR_CORRIDA WHERE conferencia_id IN
        (SELECT id FROM RDR_APP_CONFERENCIA WHERE responsavel='SEED-TESTE');
    DELETE FROM RDR_APP_CONFERENCIA WHERE responsavel='SEED-TESTE';
"""

import sys

from app import app, db
from app.models import (Recebimento, Conferencia, Corrida, InstrumentoMedicao,
                        Material, Processo, GrupoMaterial, ListaInstrumentos)
from app.metodos import (processo_sugerido, checks_aplicaveis, ORDEM_CHECKS)

APLICAR = "--aplicar" in sys.argv

# --quantos N (padrão 10)
QUANTOS = 10
if "--quantos" in sys.argv:
    QUANTOS = int(sys.argv[sys.argv.index("--quantos") + 1])

MARCA = "SEED-TESTE"          # responsavel — âncora para achar/remover depois
LOTE = max(400, QUANTOS * 5)  # quantas linhas da view examinar para achar livres


def um_por_grupo(nome_grupo):
    """Primeiro material de um grupo, para rotacionar entre grupos diferentes."""
    return db.session.scalar(
        db.select(Material).join(GrupoMaterial)
        .where(GrupoMaterial.nome == nome_grupo)
        .order_by(Material.id))


with app.app_context():

    # materiais para rotacionar (grupos diferentes = checklists diferentes)
    materiais = [m for m in (um_por_grupo('Aço'),
                             um_por_grupo('Metais'),
                             um_por_grupo('Polímeros')) if m]

    # processos de reserva, para quando o regex não reconhece o produto
    reserva = [db.session.scalar(db.select(Processo).where(Processo.nome == n))
               for n in ('Usinagem', 'Bruto', 'Pintura', 'Tratamento térmico')]
    reserva = [p for p in reserva if p]

    instrumento = db.session.scalar(db.select(ListaInstrumentos))

    # chaves que JÁ têm conferência — carregadas num set para filtrar em Python.
    # (Evita comparar Conferencia x Recebimento no SQL, que dá conflito de
    #  collation entre os dois bancos.)
    existentes = set(db.session.execute(db.select(
        Conferencia.pedido, Conferencia.item, Conferencia.nota_fiscal)).all())

    # lote de recebimentos recentes, dos quais filtramos os livres
    lote = db.session.scalars(
        db.select(Recebimento).where(Recebimento.quantidade >= 2)
        .order_by(Recebimento.dt_emissao.desc(),
                  Recebimento.pedido, Recebimento.item)
        .limit(LOTE)).all()

    escolhidos = []
    for l in lote:
        if len(escolhidos) == QUANTOS:
            break
        if (l.pedido, l.item, l.nota_fiscal) not in existentes:
            escolhidos.append(l)

    if len(escolhidos) < QUANTOS:
        print(f"Só achei {len(escolhidos)} recebimentos livres no lote de "
              f"{len(lote)}. Aumente o LOTE ou peça menos. Abortando.")
        sys.exit(1)

    print(f"Semeando {QUANTOS} conferências (já existem "
          f"{len(existentes)} no banco):\n")

    aprovadas = reprovadas = 0
    for i, l in enumerate(escolhidos):
        material = materiais[i % len(materiais)]
        qt = int(l.quantidade)

        # processo: palpite real; se o regex não reconhecer (0), usa reserva
        pid = processo_sugerido(l.produto)
        processo = db.session.get(Processo, pid) if pid else reserva[i % len(reserva)]

        conf = Conferencia(
            pedido=l.pedido, item=l.item, nota_fiscal=l.nota_fiscal,
            qt_total=qt,
            certificado=f"CERT-SEED-{i:03d}",
            material_id=material.id,
            processo_id=processo.id,
            responsavel=MARCA,
        )

        # checklist: aplicáveis = True (conforme), demais = None (N/A) — mesma
        # regra do saneamento do formulário
        aplicaveis = set(checks_aplicaveis(material.grupo.nome, processo.nome))
        for nome in ORDEM_CHECKS:
            setattr(conf, nome, True if nome in aplicaveis else None)

        # 1 em cada ~7 com não conformidade, para o index mostrar os 2 estados
        com_nc = (i % 7 == 3) and qt >= 2
        if com_nc:
            conf.pecas_reprovadas = 1
            conf.pecas_aprovadas = qt - 1
            conf.rpnc = f"RPNC-{i:03d}"
            reprovadas += 1
        else:
            conf.pecas_reprovadas = 0
            conf.pecas_aprovadas = qt
            aprovadas += 1

        # 1 corrida por conferência (soma bate com qt_total)
        conf.corridas.append(Corrida(corrida=f"LOTE-SEED-{i:03d}", qtd_corrida=qt))

        # 1 instrumento nas de índice par
        if instrumento and i % 2 == 0:
            conf.instrumentos.append(
                InstrumentoMedicao(instrumento_id=instrumento.id))

        db.session.add(conf)

    print(f"  {QUANTOS} conferências montadas: "
          f"{aprovadas} aprovadas, {reprovadas} com não conformidade")
    print(f"  datas dos recebimentos: {min(l.dt_emissao for l in escolhidos)} "
          f"-> {max(l.dt_emissao for l in escolhidos)}")

    if APLICAR:
        db.session.commit()
        total = db.session.scalar(db.select(db.func.count()).select_from(Conferencia)
                                  .where(Conferencia.responsavel == MARCA))
        print(f"\nGravadas. Total de conferências '{MARCA}' agora: {total}.")
    else:
        db.session.rollback()
        print(f"\nSimulação: nada gravado. Rode com --aplicar para valer.")
