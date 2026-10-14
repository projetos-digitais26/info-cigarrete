# Contexto do projeto

Este repositório é a base de trabalho de copy, VSLs e ofertas (infoproduto, emagrecimento,
saúde, saúde masculina/ED). Toda tarefa de copy, VSL, anúncio, página, e-mail ou
modelagem de oferta deve começar consultando a base em `base-conhecimento-copy/`.

## Como usar a base

1. Leia `base-conhecimento-copy/README.md` (índice e fluxo de trabalho).
2. Para **atualizar** uma oferta existente, siga `09-processo-de-trabalho.md` → "Nova versão".
3. Para **modelar** uma oferta validada, siga `09-processo-de-trabalho.md` → "Modelagem".
4. Antes de entregar qualquer copy de saúde, passe pelo checklist de `08-compliance.md`.

## Regras fixas

- Escrever em português do Brasil, salvo quando a oferta for para outro mercado.
- Modelar = copiar a **estrutura, a lógica e o mecanismo de persuasão**, nunca o texto literal
  nem marcas, nomes, depoimentos ou estudos de terceiros.
- Nada de depoimento, número, estudo, médico ou "pesquisa de universidade" inventado.
  Quando a copy pedir prova, marcar `[PROVA NECESSÁRIA: ...]` para o dono da oferta preencher.


# Edição de vídeo e criativos — guia do repositório

Este repositório também é a mesa de edição de criativos da agência (Reels/Stories 9:16 para Meta Ads,
B2B e varejo). Aqui o Claude "assiste" vídeos (imagem + fala + música), entende a ideia e faz:
headlines, legendas com destaque, selos, cartão final com CTA, montagem com takes de outros vídeos,
música de fundo e mixagem. Responda sempre em **português**.

Antes de editar qualquer vídeo, leia este arquivo inteiro. Ele resume o método e o que os clientes
já aprovaram ou reprovaram. Ao aprender algo novo com o usuário, **acrescente aqui** (seção
"Aprendizados" ou "Clientes") e faça commit.

## Ferramentas (pasta `ferramentas/`)
Instalação/conferência: `bash ferramentas/setup.sh`.

| Etapa | Comando |
|---|---|
| Baixar do Drive (link "qualquer pessoa com o link") | `bash ferramentas/baixar_drive.sh <link> clientes/<cliente>/<video>/bruto/video.mov` |
| "Assistir" o vídeo | `bash ferramentas/analisar_video.sh <video> <pasta>/render "nomes e termos do vídeo"` → abra `render/folha.jpg` com a ferramenta de leitura de imagem; leia cortes, volume e transcrição |
| Transcrever com tempo por palavra | `python3 ferramentas/transcrever.py <audio> <pasta>/palavras.json --prompt "Oi, lojista! Marca X, pedido mínimo de 12 peças"` |
| Ver quadros específicos | `ffmpeg -ss <t> -i video -frames:v 1 -vf scale=540:-2 x.jpg` (ou vários com `select` + `tile`) |
| Overlay (títulos/legendas/CTA) | copie um modelo de `modelos/` + `modelos/fonts/` para a pasta do vídeo e edite |
| Pré-visualizar overlay | `node ferramentas/render_overlay.js overlay.html render/stills --stills 1.5,6,12 --total N` e componha sobre o quadro do vídeo com ffmpeg `overlay` + `tile` para revisar |
| Renderizar overlay | `node ferramentas/render_overlay.js overlay.html render/ov --total N --workers 4` |
| Separar música de um vídeo do cliente | `python3 ferramentas/separar_musica.py <video> <pasta>` (fal.ai, precisa `FAL_KEY`) |
| Nivelar trilha extraída | `python3 ferramentas/nivelar_trilha.py musica.wav musica_nivelada.wav` |
| Estender música (vídeo ficou mais longo) | `python3 ferramentas/estender_musica.py <video_ou_audio> <duracao> musica.wav` |
| Mixar voz + trilha | `python3 ferramentas/mix.py <video_voz> palavras.json trilha.wav <total> <inicio_cartao_final> mix.wav` |
| Narração (voz neural grátis) | `python3 ferramentas/tts.py "texto" saida.mp3` (Thalita, pt-BR) |
| IA (vídeo/imagem/música/efeitos) | `python3 ferramentas/fal.py run <modelo> entrada.json saida/` (ex.: Veo 3.1, Kling, ElevenLabs, nano-banana) |
| Fontes do Google | `python3 ferramentas/baixar_fonte.py "Família" pasta 600,700 [--italico]` |

### Montagem e exportação (ffmpeg)
- Normalizar takes: `-vf "fps=30,scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,setsar=1,format=yuv420p"`.
- iPhone HDR (HLG/BT.2020, cores lavadas): `zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p`.
- Juntar takes: arquivo `lista.txt` com `file 's0.mp4'` … e `ffmpeg -f concat -safe 0 -i lista.txt ...`.
- Cartão final quando o vídeo termina com alguém falando: estender o último quadro
  (`tpad=stop_mode=clone:stop_duration=3`) e desfocar a partir do início do cartão
  (`split` → `gblur=sigma=28` → `fade=in:alpha=1` → `overlay`).
- Compor overlay: `ffmpeg -i base.mp4 -framerate 30 -i render/ov/o%05d.png -i audio.wav -filter_complex "[0:v][1:v]overlay=eof_action=pass,format=yuv420p[v]" -map "[v]" -map 2:a -c:v libx264 -preset slow -crf 17 -c:a aac -b:a 192k -movflags +faststart final.mp4`
- Versão para enviar no chat (limite ~30 MB): `-crf 24 -maxrate 4M -bufsize 8M -c:a aac -b:a 160k` → `*-envio.mp4`.
- Vídeo que já tem música e você não mexe no áudio: só `-map 0:a -c:a aac`.

## Método (sempre nesta ordem)
1. **Entender**: baixar, rodar `analisar_video.sh`, ver a folha de contato, ler a transcrição.
   Ler o site/Instagram do cliente quando enviado (WebFetch) para tom, cores (pegar do logo SVG/CSS)
   e fatos comerciais. **Não inventar vantagens**: só usar o que o cliente diz (site, vídeos, briefing).
2. **Mapear rostos**: na folha (linhas a cada 10% da altura), anotar onde ficam os rostos em cada trecho.
   Texto **nunca cobre rosto**. Em vídeo falado o rosto costuma ficar entre 25% e 45% da altura:
   gancho no topo (6%–24%) e legenda embaixo (~67%). Em lookbook, headlines na faixa de baixo (62%–80%).
3. **Escrever**: gancho que segmenta (ex.: "LOJISTA DE MODA FEMININA?") + promessa curta tirada da fala.
   Legendas com *destaque* nas palavras-chave. Corrigir erros do Whisper pelo contexto e **avisar o
   usuário** do que foi corrigido. Conferir grafia de nomes de pessoas e marcas.
4. **Pré-visualizar** 5–10 quadros compostos (stills) e revisar: rosto livre, leitura, contraste, nada vazio.
5. **Renderizar**, compor, mixar.
6. **Verificar**: transcrever o vídeo final (fala inteligível sobre a música), conferir duração,
   volume (`ebur128`) e emendas de música.
7. **Entregar**: versão alta + `-envio`; enviar ao usuário a versão `-envio`; commit e push.
   Na resposta: o que foi feito, tabela de headlines/tempos, e os pontos para o usuário validar.

## Aprendizados (feedback real dos clientes — seguir sempre)
- **Voz natural.** Não aplicar redução de ruído/compressão/realce na voz: o cliente achou a fala
  "condensada, estranha". `mix.py` já mantém a voz original.
- **Sem loudnorm dinâmico na mixagem final**: ele comprime a voz. Usar ganho fixo (já no `mix.py`).
  Conferir: o ganho por palavra entre original e mix deve variar < 0,1 dB.
- **Música de fundo baixa**: ~20 dB abaixo da voz durante a fala (referências aprovadas: 12–25 dB).
  Cliente reclamou de música alta.
- **Música gerada por IA (funk/“animada”) foi reprovada** ("ficaram horríveis"). Preferir a música do
  próprio cliente: extrair de um vídeo dele com `separar_musica.py` (e `nivelar_trilha.py` se estava
  abaixada sob a fala). Validar com o usuário em 1 vídeo antes de aplicar em todos.
- **Headlines com no mínimo 3 s na tela.** Com uma por corte (1,8 s) o cliente não conseguia ler.
  Menos headlines, cada uma atravessando cortes se preciso.
- **Bloco colorido das legendas cresce junto com as palavras** (sem retângulo vazio) — já no modelo 1.
- Playfair Display: usar `font-variant-numeric: lining-nums` (senão "2015" vira "2o15").
- Texto claro sobre placa/fundo da mesma cor some: usar bloco sólido (pílula) com texto escuro.
- Música curta para o vídeo novo: estender com a própria frase musical (`estender_musica.py`);
  conferir no relatório que o volume depois de cada emenda fica a menos de 1 dB do que a música original tocaria.
- Vídeo 720p: escalar para 1080×1920 com lanczos antes de compor.
- Entregar sempre também o arquivo `-envio` (< 30 MB) para o usuário ver no chat.

## Clientes
### Ste Fashion (moda feminina para revenda — B2B, São Paulo) · www.stefashion.com.br
- Público: lojistas/revendedoras de moda feminina. Tom: acolhedor, elegante, direto.
- Cores: rosa do logo `#FC97A5` (destaque), rosa escuro `#E86F86`, ameixa `#3A1621` (texto/contorno),
  creme `#FFF8F5`. Fontes: Playfair Display (títulos, itálico no destaque) + Montserrat (legendas).
- Fatos que podem ser usados: pedido mínimo **12 peças**; nasceu em **2015** em **São Paulo**;
  **+10 anos** no mercado; loja física; processo de compra organizado; atendimento voltado para
  revenda; equipe ajuda no primeiro pedido; site do atacado para conhecer peças e organizar compras;
  coleções com tendências, cores e modelagens; "o básico da Ste nunca é básico".
- Apresentadora: **Brunna** (com dois "n").
- CTA final: "Cadastre sua loja e conheça a coleção" · www.stefashion.com.br · "Acesse o site".

### Pietro Moda Fitness (atacado fitness, Brás/SP — B2B)
- Verde neon `#04FA03` sobre preto. Pedido mínimo 10 peças; +800 revendedores; +10 anos; P ao G3.
- Cartão final padrão em todos os criativos: Elev Shop Brás, Rua Tiers 558, Pari/SP, 2º corredor,
  lojas E177/E178/E179; seg–qui 6h–15h, sex–sáb 6h–13h; (11) 95447-2940;
  CTA "CLIQUE NO LINK ABAIXO / e faça seu pedido no atacado".
- Lojista do Brás gosta de música animada, mas bem atrás da voz (ver Aprendizados).

## Organização
- `clientes/<cliente>/<video>/` com `bruto/` e `render/` no `.gitignore` (arquivos grandes).
- Versionar: overlay.html, palavras.json/js, trilhas pequenas, e os MP4 finais (< 100 MB).
- Commits em português, descrevendo a entrega.
