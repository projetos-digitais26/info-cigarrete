# Plano 100% vídeo — OpenArt Pro (24.000 créditos/mês)

## Conta
- Planos que ainda não são vídeo: **386** (~20 min de tela). Os **61 vídeos já gerados** (Kling 2.5) ficam.
- Agrupados por cena em **multi-shot** (uma geração com 2–4 cortes): **164 gerações** → `geracoes-100-video.json`.

| Nível | Uso | Gerações | Segundos |
|---|---|---|---|
| premium (Seedance 2.5 ou Kling 3.0) | cenas com rosto (Márcia, Sofia, pai, Kwame…) | 84 × 10 s + 40 × 5 s | 1.040 s |
| econômico (Seedance 2.0 Fast/Mini, 50% off no Pro) | objetos, lugares, fumaça, gráficos de fundo | 23 × 10 s + 17 × 5 s | 315 s |
| quadro inicial (Nano Banana 2.1, 30% off) | 133 que faltam | — | — |

**Regra para caber em 24.000:** `1,15 × (208 × P5 + 63 × E5) + 133 × IMG ≤ 24.000`
(P5 = créditos de 5 s no premium, E5 = no econômico, IMG = por imagem; 15% de margem para refação).
Ex.: IMG 10, E5 40 → P5 até ~80. Se o premium custar mais, as cenas menos importantes descem para o econômico
(ordem de prioridade: abertura → pai → desenho/UTI → Kwame → diário → oferta).

Antes de gerar, anotar o custo que aparece no botão "Gerar" do OpenArt para: Nano Banana 2.1 (1 imagem 9:16),
Seedance 2.5 e Kling 3.0 (5 s e 10 s, 720p e 1080p, sem áudio), Seedance 2.0 Fast/Mini (5 s). Com esses números o
`produzir.py` recebe a tabela e para sozinho antes de passar de 24.000.

## Revisão desde o início (o que melhorar)
### Abertura (0:00–2:37)
- A12–A14 (13 imagens animadas) → vídeo: calendário, xícara/maço, Márcia para a câmera, esteira de fábrica.
- A10-4: celular com tela branca vazia → trocar por mão segurando o celular com a tela apagada/reflexo.
- A14-4: objeto vermelho estranho na mão da Márcia → refazer sem objeto.
- A04-1/A04-3: planos abertos genéricos da UTI → substituir por close do monitor/alarme (mais tensão).

### Bloco 2 (2:37–5:34)
- 42 imagens animadas → vídeo (principalmente varanda, isqueiro, hospital do pai, casa com cheiro de cigarro).
- C10-1…C10-4: o homem muda de rosto entre os planos → criar ref fixa `FUMANTE_C10` e refazer os 4 juntos (multi-shot).
- C11-3: punho segurando papel sem sentido → trocar por close da mão abrindo, "não foi fraqueza".
- C18-2: pai sem camisa → hospital com avental, mãos dadas.
- Desenho: a menina do desenho está loira → cabelo cacheado escuro, como a Sofia.

### Bloco 3 em diante
- Já com os prompts corrigidos (sem barras vazias, moderação). Tudo direto em vídeo.

### Pendências de copy (não dependem de vídeo)
- C94: "menos que 3 dias de cigarro" (3 × R$ 12 = R$ 36 < R$ 37) → ajustar preço do maço ou dias.
- C92/C93: âncora (narração diz 300/200/100) e valor da parcela 12x.
- Fontes: recaída (C37g), prevalência em Gana (C45), linha do tempo de recuperação (C98).
- Material real: depoimentos (C83), prints (C84), checkout (C100).
