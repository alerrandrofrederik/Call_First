"""Regras de limpeza compartilhadas pela silver e pela tarefa consultar_cnpj, como expressões PySpark.

- e-mail normalizado: minúsculas e sem espaços nas pontas (PRD RF-06).
- CNPJ normalizado: só os dígitos; válido quando tem 14 dígitos, não é repetição de um dígito e
  os 2 dígitos verificadores (módulo 11) conferem (PRD RF-05).
- DDD válido: está na lista de DDDs em uso no Brasil (Anatel). Só sinaliza (contrato crm, ponto aberto P-05).
"""
from pyspark.sql import Column
from pyspark.sql import functions as F

# DDDs em uso no Brasil (plano de numeração da Anatel).
DDDS_VALIDOS = [
    11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 24, 27, 28, 31, 32, 33, 34, 35, 37, 38,
    41, 42, 43, 44, 45, 46, 47, 48, 49, 51, 53, 54, 55, 61, 62, 63, 64, 65, 66, 67, 68, 69,
    71, 73, 74, 75, 77, 79, 81, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 98, 99,
]

_PESOS_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_PESOS_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]


def email_norm(col: Column) -> Column:
    return F.lower(F.trim(col))


def cnpj_norm(col: Column) -> Column:
    """Só os dígitos do CNPJ; nulo quando não sobra nenhum."""
    d = F.regexp_replace(col, r"\D", "")
    return F.when(F.length(d) > 0, d)


def _digito(d: Column, pesos: list[int]) -> Column:
    soma = sum(F.substring(d, i + 1, 1).cast("int") * p for i, p in enumerate(pesos))
    resto = soma % 11
    return F.when(resto < 2, F.lit(0)).otherwise(11 - resto)


def cnpj_valido(col: Column) -> Column:
    """True/False para um CNPJ já normalizado; nulo quando não há CNPJ."""
    d = col
    ok = (
        d.rlike(r"^\d{14}$")
        & ~d.rlike(r"^(\d)\1{13}$")
        & (F.substring(d, 13, 1).cast("int") == _digito(d, _PESOS_1))
        & (F.substring(d, 14, 1).cast("int") == _digito(d, _PESOS_2))
    )
    return F.when(d.isNull(), F.lit(None).cast("boolean")).otherwise(F.coalesce(ok, F.lit(False)))


def ddd_valido(telefone: Column) -> Column:
    """True quando o DDD entre parênteses está em uso; nulo quando não há telefone."""
    ddd = F.regexp_extract(telefone, r"^\((\d{2})\)", 1)
    return F.when(telefone.isNull(), F.lit(None).cast("boolean")).otherwise(
        ddd.cast("int").isin(DDDS_VALIDOS)
    )
