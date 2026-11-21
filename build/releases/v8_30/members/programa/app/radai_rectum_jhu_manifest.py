# -*- coding: utf-8 -*-
"""Origem, tamanho e integridade dos pesos JHU/MICA; usados somente a partir do disco."""
IDENT = "jhu_rectum"
RELEASE = "https://github.com/JHU-MICA/TwoStepMalePelvicCTSeg/releases/download/models/"
ARQUIVOS = {
    nome: {"url": RELEASE + nome, "bytes": tamanho, "sha256": digest}
    for nome, tamanho, digest in (
        ("model_coarse.pt", 9366163, "c509d9b19dab31b54fe0c4956a59937862ca1d63118cf1ec1f5aec60198597f8"),
        ("model_fine_rectum.pt", 91109045, "4832b7a832ce2b3babfb9d209a27952b0e69fc717c77e868147748bbedaaef27"),
        ("model_fine_prostate.pt", 22596491, "0e116744b554c370706868b4193ae785633a252f201c19ce64f602578ab57dd3"),
        ("data_fingerprints.zip", 1349, "abf7ba1324373e60a34f1c7bc8b7036d0dda6f0eadcd9028c3799c0bc6da4fb6"),
    )
}

