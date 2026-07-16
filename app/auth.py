import os
from functools import wraps

import requests
from flask import redirect, session, url_for


class ProtheusIndisponivel(Exception):
    """O ERP não respondeu ou respondeu algo inesperado."""


def autenticar_no_protheus(usuario, senha):

    usuario = (usuario or "").strip()
    if not usuario or not senha:
        return None

    try:
        resposta = requests.get(
            f"{os.getenv('PROTHEUS_BASE_URL', '').rstrip('/')}/AUTHUSER/WUSER",
            params={"USR": usuario, "PWD": senha},
            auth=(os.getenv("PROTHEUS_USER", ""),
                  os.getenv("PROTHEUS_PASSWORD", "")),
            timeout=float(os.getenv("PROTHEUS_TIMEOUT", "10")),
        )
    except requests.RequestException:
        raise ProtheusIndisponivel()

    corpo = resposta.text.lower()
    if "senha invalida" in corpo or "usuario invalido" in corpo:
        return None

    if resposta.status_code == 200:
        try:
            dados = resposta.json()
        except ValueError:
            raise ProtheusIndisponivel()
        for linha in dados if isinstance(dados, list) else [dados]:
            if isinstance(linha, dict) and linha.get("User_Name"):
                return {"user_id": linha.get("User_Id"),
                        "user_name": linha["User_Name"]}
        return None

    raise ProtheusIndisponivel()


def login_obrigatorio(funcao):
    @wraps(funcao)
    def verificacao(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return funcao(*args, **kwargs)
    return verificacao
