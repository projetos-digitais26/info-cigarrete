// Renderiza um overlay HTML (com window.render(t) determinístico) em PNGs transparentes, quadro a quadro.
// Uso: node ferramentas/render_overlay.js <overlay.html> <saida_dir> --total <segundos> [--fps 30] [--workers 4] [--stills 1.5,3,8.2]
// Depois: ffmpeg -i base.mp4 -framerate 30 -i <saida_dir>/o%05d.png -i audio.wav \
//           -filter_complex "[0:v][1:v]overlay=eof_action=pass,format=yuv420p[v]" -map "[v]" -map 2:a ...
const path = require('path'), fs = require('fs');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) {
  const g = require('child_process').execSync('npm root -g').toString().trim();
  ({ chromium } = require(path.join(g, 'playwright')));
}
const [html, out, ...args] = process.argv.slice(2);
if (!html || !out) { console.log('uso: node render_overlay.js <overlay.html> <saida_dir> --total N [--stills t1,t2]'); process.exit(1); }
const opt = k => args.includes(k) ? args[args.indexOf(k) + 1] : null;
const FPS = +(opt('--fps') || 30), TOTAL = +(opt('--total') || 0), workers = +(opt('--workers') || 4);
const stills = opt('--stills') ? opt('--stills').split(',').map(Number) : null;
if (!stills && !TOTAL) { console.log('informe --total (duração em segundos)'); process.exit(1); }
// Chromium do ambiente (Playwright pré-instalado em /opt/pw-browsers) ou o padrão do Playwright
function exe() {
  const base = process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers';
  try { for (const d of fs.readdirSync(base).filter(d => /^chromium-\d+$/.test(d)).sort().reverse()) {
    const p = path.join(base, d, 'chrome-linux', 'chrome'); if (fs.existsSync(p)) return p; } } catch (e) {}
  return undefined;
}
const url = 'file://' + path.resolve(html);
async function worker(times, names) {
  const b = await chromium.launch({ executablePath: exe() });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto(url);
  await p.evaluate(async () => { await document.fonts.ready; });
  await p.waitForFunction(() => [...document.images].every(i => i.complete) && window.ready === true);   // o overlay sinaliza window.ready = true quando terminou de preparar
  for (let i = 0; i < times.length; i++) {
    await p.evaluate(t => window.render(t), times[i]);
    await p.screenshot({ path: path.join(out, names[i]), omitBackground: true, type: 'png' });
  }
  await b.close();
}
(async () => {
  fs.mkdirSync(out, { recursive: true });
  let times, names;
  if (stills) { times = stills; names = stills.map(t => `o_${t.toFixed(2)}.png`); }
  else { const n = Math.round(TOTAL * FPS); times = [...Array(n).keys()].map(i => i / FPS); names = times.map((_, i) => `o${String(i).padStart(5, '0')}.png`); }
  const ch = [...Array(workers)].map(() => ({ t: [], n: [] }));
  times.forEach((t, i) => { ch[i % workers].t.push(t); ch[i % workers].n.push(names[i]); });
  const t0 = Date.now();
  await Promise.all(ch.filter(c => c.t.length).map(c => worker(c.t, c.n)));
  console.log(`ok ${times.length} quadros em ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${out}`);
})();
