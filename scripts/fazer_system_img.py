"""Gera system.img.ext4 (sparse do Android, so blocos RAW) a partir de uma imagem crua da particao system
ou de um clone cru do eMMC inteiro da central do Fiat Argo (Multilaser, AC8317, V1.0.09R8).

Uso:
  python fazer_system_img.py --particao system_cru.img  system.img.ext4
  python fazer_system_img.py --clone   emmc_inteiro.img  system.img.ext4

O recovery AC8317 TC V1.0.4.4 ("Update system") so entende chunks RAW (0xCAC1) e DONT_CARE (0xCAC3).
Aqui tudo vai como RAW, em chunks de 1 MiB, para nao deixar restos da system antiga e nao estourar a memoria.
"""
import argparse
import hashlib
import struct

BLK = 4096
SYSTEM_INICIO = 0x1200000      # offset da system no eMMC
SYSTEM_TAMANHO = 0x32000000    # 800 MiB
SYSTEM_MD5 = "2599852d6cad052892fc0a0b4e444112"  # system de fabrica V1.0.09R8


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--particao")
    g.add_argument("--clone")
    ap.add_argument("saida")
    a = ap.parse_args()
    if a.clone:
        with open(a.clone, "rb") as f:
            f.seek(SYSTEM_INICIO)
            dados = f.read(SYSTEM_TAMANHO)
    else:
        dados = open(a.particao, "rb").read()
    assert len(dados) == SYSTEM_TAMANHO, f"tamanho inesperado: {len(dados)}"
    md5 = hashlib.md5(dados).hexdigest()
    print("md5 da system:", md5, "(fabrica V1.0.09R8)" if md5 == SYSTEM_MD5 else "(DIFERENTE da de fabrica conhecida)")

    total = len(dados) // BLK
    passo = 256  # 1 MiB
    n = (total + passo - 1) // passo
    with open(a.saida, "wb") as out:
        out.write(struct.pack("<IHHHHIIII", 0xED26FF3A, 1, 0, 28, 12, BLK, total, n, 0))
        for i in range(0, total, passo):
            q = min(passo, total - i)
            out.write(struct.pack("<HHII", 0xCAC1, 0, q, 12 + q * BLK))
            out.write(dados[i * BLK:(i + q) * BLK])
    print("gerado:", a.saida, hashlib.md5(open(a.saida, "rb").read()).hexdigest())


if __name__ == "__main__":
    main()
