"""Monta update/update.img para o recovery AC8317 (central Multilaser do Fiat Argo)
a partir do clone cru do eMMC de uma central igual.

Conteudo do zip (formato descoberto no binario /sbin/recovery V1.0.4.4):
  scatter.mmcboot.ext4.xml  tabela de particoes IDENTICA a gravada no eMMC (offset 0x3ffe00, "PTBL")
  recovery.gz               particao recovery (obrigatoria; se igual a instalada, nao regrava)
  system.img.ext4           particao system em sparse: RAW 0xCAC1 nos blocos usados, DONT_CARE 0xCAC3 nos livres
                            (tem que caber no tmpfs /tmp de 720m; FILL/CRC nao sao aceitos pelo recovery)
  md5.txt                   "<md5>  <arquivo>" de cada arquivo acima

So as particoes com imagename no XML sao gravadas (aqui: so a system).
Uso: python montar_update_img.py <clone.img> <pasta_saida>
"""
import hashlib
import os
import struct
import sys
import zipfile

MiB = 1024 * 1024
BLK = 4096

# (nome, tipo, mount, inicio, tamanho) lidos da tabela PTBL do clone
TABELA = [
    ("preloader", "raw", 0, 0x0, 0x10000), ("datazone", "raw", 0, 0x10000, 0x1000),
    ("uboot", "raw", 0, 0x11000, 0x3EF000), ("env", "raw", 0, 0x400000, 0x200000),
    ("arm2", "raw", 0, 0x600000, 0x200000), ("logo", "raw", 0, 0x800000, 0x400000),
    ("kernel", "raw", 0, 0xC00000, 0x400000), ("rootfs", "raw", 0, 0x1000000, 0x200000),
    ("system", "ext4", 1, 0x1200000, 0x32000000), ("data", "ext4", 1, 0x33200000, 0x7D000000),
    ("cache", "ext4", 1, 0xB0200000, 0x6400000), ("recovery", "raw", 0, 0xB6600000, 0x400000),
    ("misc", "raw", 0, 0xB6A00000, 0x200000), ("backup", "ext4", 1, 0xB6C00000, 0x4600000),
    ("metazone", "raw", 0, 0xBB200000, 0x400000), ("dvp", "raw", 0, 0xBB600000, 0x400000),
    ("data4write", "ext4", 1, 0xBBA00000, 0x7D000000),
]
GRAVAR = {"system": "system.img.ext4"}
ESPERADO = {"system": "2599852d6cad052892fc0a0b4e444112", "recovery": "34068a79aa239c972471142171d8df3a"}


def ler(f, ini, tam):
    f.seek(ini)
    d = f.read(tam)
    assert len(d) == tam
    return d


def sparse_raw(dados, chunk_blocos=256):
    assert len(dados) % BLK == 0
    total = len(dados) // BLK
    n = (total + chunk_blocos - 1) // chunk_blocos
    partes = [struct.pack("<IHHHHIIII", 0xED26FF3A, 1, 0, 28, 12, BLK, total, n, 0)]
    for i in range(0, total, chunk_blocos):
        q = min(chunk_blocos, total - i)
        partes.append(struct.pack("<HHII", 0xCAC1, 0, q, 12 + q * BLK))
        partes.append(dados[i * BLK:(i + q) * BLK])
    return b"".join(partes)


def blocos_usados_ext4(dados):
    """Mapa de blocos ocupados segundo os bitmaps do ext4 (bloco 4 KiB, descritor de 32 bytes)."""
    sb = dados[1024:2048]
    total, = struct.unpack_from("<I", sb, 4)
    primeiro, log_bs, = struct.unpack_from("<II", sb, 20)
    por_grupo, = struct.unpack_from("<I", sb, 32)
    assert struct.unpack_from("<H", sb, 56)[0] == 0xEF53 and (1024 << log_bs) == BLK
    grupos = (total + por_grupo - 1) // por_grupo
    gdt = (primeiro + 1) * BLK
    usados = bytearray(total)
    for g in range(grupos):
        bitmap, = struct.unpack_from("<I", dados, gdt + g * 32)
        flags, = struct.unpack_from("<H", dados, gdt + g * 32 + 18)
        n = min(por_grupo, total - g * por_grupo)
        if flags & 2:  # BLOCK_UNINIT: bitmap nao gravado; manda o grupo inteiro por seguranca
            usados[g * por_grupo:g * por_grupo + n] = b"\1" * n
            continue
        bm = dados[bitmap * BLK:bitmap * BLK + BLK]
        for b in range(n):
            if bm[b >> 3] >> (b & 7) & 1:
                usados[g * por_grupo + b] = 1
    return usados, total


def sparse_usados(dados, max_raw=256):
    """Sparse so com RAW (0xCAC1) para blocos usados e DONT_CARE (0xCAC3) para os livres.
    O gravador do recovery (0x8d08) so aceita esses dois tipos."""
    usados, total = blocos_usados_ext4(dados)
    assert total * BLK == len(dados)
    chunks, i = [], 0
    while i < total:
        j, tipo = i, usados[i]
        lim = total if not tipo else min(total, i + max_raw)
        while j < lim and usados[j] == tipo:
            j += 1
        q = j - i
        if tipo:
            chunks.append(struct.pack("<HHII", 0xCAC1, 0, q, 12 + q * BLK) + dados[i * BLK:j * BLK])
        else:
            chunks.append(struct.pack("<HHII", 0xCAC3, 0, q, 12))
        i = j
    cab = struct.pack("<IHHHHIIII", 0xED26FF3A, 1, 0, 28, 12, BLK, total, len(chunks), 0)
    return cab + b"".join(chunks)


def main():
    clone, saida = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.join(saida, "update"), exist_ok=True)
    arquivos = {}
    with open(clone, "rb") as f:
        system = ler(f, 0x1200000, 0x32000000)
        recovery = ler(f, 0xB6600000, 0x400000)
    assert hashlib.md5(system).hexdigest() == ESPERADO["system"], "system do clone nao confere"
    assert hashlib.md5(recovery).hexdigest() == ESPERADO["recovery"], "recovery do clone nao confere"
    # /tmp do recovery e tmpfs de 720m: a system crua (800 MiB) nao cabe; so os blocos usados (~550 MiB).
    arquivos["system.img.ext4"] = sparse_usados(system)
    assert len(arquivos["system.img.ext4"]) < 640 * MiB, "sparse grande demais para o /tmp (720m)"
    arquivos["recovery.gz"] = recovery

    # O parser do recovery (0xecdc) so procura <FLASH> como elemento de topo do documento;
    # dentro de <root> ele e ignorado, a lista fica vazia e o recovery cai (0xf4bc le NULL).
    linhas = ['<?xml version="1.0" encoding="UTF-8"?>', "<FLASH>"]
    for nome, tipo, mount, ini, tam in TABELA:
        img = GRAVAR.get(nome, "")
        linhas.append(f'  <partition name="{nome}" type="{tipo}" mount="{mount}" '
                      f'startaddress="{ini:#x}" size="{tam:#x}" imagename="{img}"></partition>')
    linhas += ["</FLASH>", ""]
    arquivos["scatter.mmcboot.ext4.xml"] = "\n".join(linhas).encode()

    md5 = "".join(f"{hashlib.md5(d).hexdigest()}  {n}\n" for n, d in arquivos.items())
    arquivos["md5.txt"] = md5.encode()

    destino = os.path.join(saida, "update", "update.img")
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_STORED) as z:
        for n in ("md5.txt", "scatter.mmcboot.ext4.xml", "recovery.gz", "system.img.ext4"):
            z.writestr(n, arquivos[n])
    print(md5, end="")
    print("update.img:", os.path.getsize(destino), "bytes")
    print("md5 update.img:", hashlib.md5(open(destino, "rb").read()).hexdigest())


if __name__ == "__main__":
    main()
