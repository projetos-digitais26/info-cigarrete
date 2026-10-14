# Bíblia visual — VSL V2 PT-BR "O Truque do Primeiro Cigarro do Dia"

Cinematografia 100% em vídeo, formato **story 9:16 (1080×1920)**, sincronizada com
`audio/vsl-v2-pt-elevenlabs.mp3` (26,7 min). Tempos e duração de cada cena: `cenas-tempo.json`.
Planos: `planos.json` (gerado a partir da decupagem `decupagem-pt-br.md`).

## 1. Regras de ritmo (retenção)

| Regra | Valor |
|---|---|
| Plano mais longo | **4 s** na abertura (0:00–2:40) e no bloco de medo; **6 s** no resto; nunca um plano parado acima disso |
| Reset de atenção | no máximo **a cada 12 s** há uma quebra de padrão (lista abaixo); nos 🔁 do roteiro, quebra obrigatória |
| Rosto da Márcia para a câmera | sempre com micro-movimento (push-in lento 3–5%, respiração, piscar); nunca still |
| Texto na tela | só o 🅣 do roteiro + legenda palavra a palavra; **nunca** pedir texto ao modelo de vídeo |
| Legenda | faixa 62–72% da altura; rosto fica entre 18% e 48% (enquadrar os planos com isso em mente) |

### Caixa de ferramentas de quebra de padrão (campo `quebra` do plano)
- `corte_seco` — corte duro de luz/cor oposta (frio → quente, escuro → claro)
- `preto` — 6–30 quadros de tela preta com som (ou silêncio)
- `flash_branco` — 2–4 quadros brancos + impacto grave
- `zoom_punch` — zoom digital de 100% → 115% em 4 quadros no começo da palavra-chave
- `freeze` — congela o quadro 0,5–1 s + whoosh, com o 🅣 entrando
- `speed_ramp` — câmera lenta que acelera (ou o inverso) no meio do plano
- `match_cut` — o mesmo enquadramento/objeto em outro tempo (mãos A01 ↔ C109b, cozinha A07 ↔ C78, isqueiro C14 ↔ C108)
- `whip` — chicote lateral (motion blur) entre dois lugares
- `glitch` — 3–5 quadros de RGB split/scanline (só no bloco da indústria e da ciência)
- `pov` — câmera subjetiva do espectador (C83c, C106b)
- `split` — tela dividida vertical (C106 dois caminhos, C33 sorriso × cinzeiro)

## 2. Look por fase (campo `fase` de `cenas-tempo.json` → color grade na montagem)

| Fase | Look | Grade (ffmpeg) |
|---|---|---|
| uti, hospital | azul frio, verde hospitalar, dessaturado, grão forte, luz de monitor | `eq=saturation=.55:contrast=1.08,colorbalance=bs=.12:gm=.05,noise=alls=14:allf=t` |
| silencio | preto / quase preto | — |
| memoria, piano, ninar | quente âmbar, halation suave, grão médio, 24 fps de lembrança | `eq=saturation=.9,colorbalance=rs=.08:gm=.04,noise=alls=9:allf=t` |
| tensao, medo, pulso | contraste alto, sombras esmagadas, vermelho pontual | `eq=contrast=1.18:saturation=.8,vignette=PI/4` |
| fogo (indústria/recaída) | laranja-preto, fumaça, chama como única luz | `eq=contrast=1.15,colorbalance=rh=.1:bs=-.05` |
| gana | dourado, pôr do sol, cores vivas do kente, poeira no ar | `eq=saturation=1.15,colorbalance=rh=.06:gh=.04` |
| ciencia | branco frio de tela, ciano, limpo | `eq=saturation=.85,colorbalance=bs=.06` |
| diario, leve, vitoria | manhã quente, janela estourada, pele bonita | `eq=saturation=1.05:gamma=1.03` |
| filho | quente íntimo, luz de abajur | `eq=saturation=.95,colorbalance=rs=.05` |
| manada | quente, várias casas diferentes, mosaico | — |
| oferta, fechamento | limpo, escuro premium + dourado (gráficos) ou manhã quente | — |

Todas as fases recebem leve grão de filme e `vignette` sutil para unir IA + gráficos.

## 3. Personagens fixos (gerar 1 folha de referência de cada antes de qualquer plano)

Use estes textos **idênticos** em todos os prompts (campo `refs`). Pessoas fictícias; nenhum rosto real.

| ref | Descrição para o prompt (EN) |
|---|---|
| `MARCIA_43_UTI` | Brazilian woman, 43, light-brown skin, shoulder-length dark wavy hair messy on pillow, pale and sweaty, dark circles, oxygen mask, hospital gown, IV line and pulse oximeter on finger |
| `MARCIA_42` | same woman at 42 (smoker years): Brazilian, light-brown skin, dark wavy hair tied loosely, tired eyes, dark circles, slightly yellowed teeth, grey cotton t-shirt or simple office blouse |
| `MARCIA_44` | same woman today, 44, healthy: Brazilian, light-brown skin, dark wavy shoulder-length hair, warm brown eyes, natural light makeup, cream knit sweater, small gold necklace, calm half-smile |
| `SOFIA_8` / `SOFIA_9` | Brazilian girl, 8–9, light-brown skin, curly dark-brown hair in two puffs, big brown eyes, yellow t-shirt with small star |
| `SOFIA_12` | same girl at 12, curly hair down, pajamas with stars |
| `LUCIANO` | Brazilian man, 46, tan skin, short black hair greying at temples, light beard, gentle face, blue button shirt |
| `PAI` | Brazilian man, 60s, white-grey hair, thick grey moustache, tan wrinkled skin, short-sleeve plaid shirt with a silver lighter in the chest pocket; at 67 in hospital: thin, oxygen mask |
| `KWAME` | Ghanaian elder, about 75, dark skin, short white hair and short white beard, deep calm eyes, kente-pattern cloth draped over one shoulder, wooden carved chair |
| `KOFI` | Ghanaian man, 50, dark skin, shaved head, wide smile, colorful printed shirt |
| `CUNHADO` | Brazilian man, 50, stocky, cap, smoking at a backyard barbecue |

## 4. Objetos-âncora e locações (aparecem várias vezes → mesma referência)

| ref | Descrição |
|---|---|
| `ISQUEIRO` | old silver flip lighter, worn engraving, scratches |
| `DESENHO` | child's crayon drawing on lined paper: a woman with a cigarette crossed by a red X, a crying girl beside her (sem texto legível no vídeo; a frase entra como 🅣) |
| `FRASCOS` | two small glass jars on rustic wood: one with cigarette halves and coarse salt, one with black peppercorns and salt |
| `CADERNO` | simple brown kraft notebook, handwriting in blue pen |
| `COZINHA` | small Brazilian apartment kitchen, white tiles, window over the sink, wooden chair, glass coffee pot (A07, C78, C83c — mesma câmera) |
| `UTI` | ICU room at night, blue monitor light, ventilator, bed rails |
| `VARANDA` | simple Brazilian house porch, plastic chairs, plants, sunset |
| `VILAREJO` | Ghanaian village, mud-brick houses, red dirt road, baobab, golden hour |
| `SERPENTE` | serpent made of cigarette smoke, translucent grey, glowing ember eyes |

## 5. Roteamento de modelos (campo `modelo`)

| Tipo | Uso | Modelo (fal.ai) | Preço de referência* |
|---|---|---|---|
| `hero` | rostos, emoção, personagens fixos | quadro-chave com `nano-banana` (edição com refs) → **Veo 3.1 image-to-video**, sem áudio | US$ 0,20/s (Fast: US$ 0,10/s) |
| `acao` | personagens em movimento, mãos, objetos-âncora | quadro-chave → **Kling 3.0 Pro image-to-video**, sem áudio | US$ 0,112/s |
| `broll` | paisagens, multidões, ambulância, fábrica, montagem | **Kling 2.5 Turbo Pro** (texto ou imagem → vídeo) | US$ 0,35 a cada 5 s |
| `fx` | serpente de fumaça, animação 3D do pulmão/artéria | Veo 3.1 texto → vídeo | US$ 0,20/s |
| `grafico` | cartões, calendário, gráfico, calculadora, preço, app, FAQ, selo | **sem IA**: overlay HTML (`ferramentas/render_overlay.js`) sobre fundo de vídeo | — |
| `preto` | tela preta | — | — |

\* fal.ai, out/2026; confirmar antes de gerar.

O áudio é sempre o da VSL (os vídeos são gerados **sem áudio**); efeitos já estão na mixagem.

## 6. Modelo de prompt

- **keyframe** (imagem, EN): `[refs] + [ação congelada] + [enquadramento 9:16, posição do rosto] + [luz da fase] + "cinematic still, 35mm film, shallow depth of field, photorealistic, no text, no logos"`
- **motion** (vídeo, EN): `[movimento do sujeito] + [movimento de câmera] + [ritmo]`. Uma ação por plano. 5 s gerados, uso de 1,5–5 s.
- Proibido no prompt: marcas de cigarro legíveis, texto, sangue, nudez, crianças fumando, rostos de pessoas reais.

## 7. Cuidados (Meta / saúde)

- Cenas dramatizadas: manter no vídeo o selo discreto **"Cenas dramatizadas"** nas cenas de hospital e na história, e o rodapé da página.
- Depoimentos (C83) e prints (C84): **somente material real autorizado**; a IA não gera depoimento nem print.
- Infográficos de saúde só com os dados com fonte já marcados no roteiro.
