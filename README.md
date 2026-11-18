# Recuperação da central multimídia 9" do Fiat Argo (Multilaser / Mopar)

Guia e imagem para **reinstalar o Android** da central de fábrica de 9" do Fiat Argo quando ela
fica **presa no "Android system recovery"** (robô verde com triângulo vermelho) e não liga mais o sistema.

Testado em 18/11/2026: uma central presa no recovery voltou ao Android normal seguindo este guia.

> **Não oficial.** Projeto de dono para dono, sem vínculo com Fiat, Stellantis ou Multilaser.
> O software pertence aos fabricantes. Use por sua conta e risco.

## Serve para a sua central?

Confira **tudo** abaixo antes de usar:

| Item | Valor esperado | Onde ver |
|---|---|---|
| Central | Multilaser "FIAT Módulo X6H 9"", Mopar | Etiqueta atrás da central |
| FCA PN | `52128799` | Etiqueta |
| SW Version | `V1.0.09R8` | Etiqueta, ou Config > Sobre (se ainda ligasse) |
| Tela do recovery | `AC8317 TC V1.0.4.4 Android system recovery <3e>` | Primeira linha da tela do recovery |

Se a versão do software for outra, **não use**: a imagem é da `V1.0.09R8`
(`Q9025FT-F01CJ2-Q02-V1.0.09R8-PT`). Se o menu do recovery for diferente, também não use.

## O que você precisa

- **Cartão micro SD de 4 a 32 GB** (o leitor da central é antigo; acima de 32 GB pode não funcionar).
- Computador para preparar o cartão.
- O arquivo **`system.img.ext4.zip`** da página de [Releases](../../releases) deste repositório.

## Passo a passo

### 1. Preparar o cartão (no computador)

1. Baixe `system.img.ext4.zip` e confira o MD5 (seção [Conferência](#conferência)).
2. Descompacte. Vai sair **um arquivo só**: `system.img.ext4` (839 MB).
3. Formate o cartão em **FAT32** (no Windows: clique com o botão direito no cartão > Formatar > FAT32).
4. Copie `system.img.ext4` para a **raiz** do cartão. Não coloque dentro de pasta e não renomeie.
5. Ejete o cartão com segurança.

### 2. Na central

1. Com a central no recovery, coloque o cartão na entrada de cartão da central.
2. Confira que o título do menu diz **"Update image from SD Card"**.
   Se estiver "USB Disk", toque em **Image from U Disk** para alternar de volta para o SD.
3. Toque em **Update system** (penúltima opção da lista).
4. Aparece `Update system ...` e depois
   `update_ext4_partition_from_file dev(/dev/block/system) ... file(/ext_sdcard2/system.img.ext4)`.
   **Espere** (2 a 10 minutos). Não desligue o carro, não tire o cartão, não toque na tela.
5. Quando aparecer **"Update system from /ext_sdcard2/. Update is successful."**, toque em **Reboot system**.
6. O primeiro boot demora mais ("Aguarde, sistema inicializando..." e depois "Inicializando, por favor aguarde..."). Espere.

### O que NÃO fazer

- **Não use "Auto Update"** para isso: pelo menu ele sempre falha com `open /tmp/md5.txt error` (não estraga nada, só não funciona).
- **Não use** "Update uboot", "Update kernel", "Update recovery" e outras "Update ..." sem saber o que está gravando.
  "Update uboot" errado pode deixar a central sem ligar de vez.

## O que essa imagem faz e não faz

- Regrava **só a partição `system`** (o Android de fábrica, 800 MB).
- **Não mexe** no bootloader, kernel, recovery, logo, nem nos seus dados e configurações (`data`).
- Resolve quando o problema está nos arquivos do sistema (arquivo do sistema apagado, alterado ou corrompido).
- **Não resolve** defeito de hardware (memória eMMC com defeito, placa queimada) nem problema em outras partições.

## Mensagens possíveis

| Mensagem | Significado |
|---|---|
| `Image file isn't exist!!!` | Não achou `system.img.ext4` na raiz do cartão (nome errado, dentro de pasta, cartão não FAT32 ou não reconhecido). |
| `Update is successful.` | Gravou. Toque em Reboot system. |
| `Image file is damaged!!!` | Arquivo corrompido: baixe de novo e confira o MD5. |
| Volta ao recovery depois de gravar | O problema não está na `system`. Procure uma assistência técnica. |

## Conferência

| Arquivo | MD5 |
|---|---|
| `system.img.ext4` (839 MB, descompactado) | `00a533a9ce1e038bcbf124156c7178b4` |
| Partição `system` resultante (800 MiB) | `2599852d6cad052892fc0a0b4e444112` |

O MD5 do `.zip` está na página do Release.

No Windows (PowerShell): `Get-FileHash .\system.img.ext4 -Algorithm MD5`

## Como a imagem foi feita

- Origem: **cópia byte a byte** do eMMC de uma central igual funcionando (mesma versão `V1.0.09R8`),
  com o MD5 de cada partição conferido contra o aparelho.
- Só a partição `system` foi publicada. A `system` contém apenas apps de fábrica (Multilaser/Roadrover, Android, Google);
  **nenhum dado pessoal** (contas, redes Wi-Fi, celulares pareados ficam na partição `data`, que **não** está aqui).
- Formato: imagem *sparse* do Android só com blocos RAW (`0xCAC1`), que é o que a opção "Update system"
  do recovery `AC8317 TC V1.0.4.4` aceita (`update_ext4_partition_from_file`).
- Script usado: [`scripts/fazer_system_img.py`](scripts/fazer_system_img.py).

## Detalhes técnicos do recovery (para quem quer ir além)

Recovery `AC8317 TC V1.0.4.4` (Autochips AC8317, Android 4.2.2), analisado a partir do binário `/sbin/recovery`:

- As opções **"Update X"** leem `<raiz do cartão>/<arquivo>` conforme a `recovery.fstab`, sem checar MD5:
  `system` → `system.img.ext4`, `kernel` → `uImage`, `rootfs` → `ramdisk.gz`, `recovery` → `recovery.gz`,
  `logo` → `logo.mrf`, `metazone` → `metazone.bin`, `dvp` → `target.bin`, `arm2` → `arm2.bin`, `uboot` → `u-boot.bin`.
- Cartão SD com partição = `/ext_sdcard2/` (`mmcblk1p1`); sem partição = `/ext_sdcard1/`; pendrive = `/udisk1/` (`sda`).
- **"Auto Update"** lê `update/update.img` (zip com `md5.txt`, `scatter.mmcboot.ext4.xml`, `recovery.gz` e imagens),
  mas pelo menu falha porque o `md5.txt` só é extraído quando o recovery é chamado por comando de boot.
- Tabela de partições (cmdline do kernel e tabela `PTBL` no eMMC em `0x3ffe00`):

| Partição | Início | Tamanho | Tipo |
|---|---|---|---|
| preloader | 0x0 | 64 KiB | raw |
| datazone | 0x10000 | 4 KiB | raw |
| uboot | 0x11000 | 0x3ef000 | raw |
| env | 0x400000 | 2 MiB | raw |
| arm2 | 0x600000 | 2 MiB | raw |
| logo | 0x800000 | 4 MiB | raw |
| kernel | 0xc00000 | 4 MiB | raw |
| rootfs | 0x1000000 | 2 MiB | raw |
| system | 0x1200000 | 800 MiB | ext4 |
| data | 0x33200000 | 2000 MiB | ext4 |
| cache | 0xb0200000 | 100 MiB | ext4 |
| recovery | 0xb6600000 | 4 MiB | raw |
| misc | 0xb6a00000 | 2 MiB | raw |
| backup | 0xb6c00000 | 70 MiB | ext4 |
| metazone | 0xbb200000 | 4 MiB | raw |
| dvp | 0xbb600000 | 4 MiB | raw |
| data4write | 0xbba00000 | 2000 MiB | ext4 |
| usrdata | resto | ~10 GiB | vfat (armazenamento interno) |
