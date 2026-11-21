def confirmacoes(consentimento):
    """Simula as escolhas da estação de teste. Cada profissional confirma as suas na interface."""
    return {"itens": [chave for chave, _, _ in consentimento.PONTOS],
            "catalogo_sha256": consentimento.catalogo_termos.catalogo()[0],
            "ensino_pesquisa": True}
