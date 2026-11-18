"""Carrusel de Instagram (1080x1350) — Fin de año Grupo San Cristóbal.
Marca: Mirian Olivera · Organizadora de Seguros.
Uso: python3 carrusel_san_cristobal.py  -> entrega/san_cristobal_0N.png
"""
from pathlib import Path
import subprocess

BASE = Path(__file__).resolve().parent
A = (BASE / "assets").as_uri()
OUT = BASE / "entrega"
OUT.mkdir(exist_ok=True)

CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700;800&family=Lato:wght@400;700&display=swap');
:root {{ --violeta:#951b81; --celeste:#56c2e3; --negro:#1D1D1B;
        --deg: linear-gradient(135deg, #56c2e3 0%, #56c2e3 18%, #951b81 52%, #951b81 100%); }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html,body {{ width:1080px; height:1350px; overflow:hidden; }}
body {{ font-family:'Lato',sans-serif; color:var(--negro); background:#fff; position:relative; }}
.mont {{ font-family:'Montserrat',sans-serif; }}
.full {{ position:absolute; inset:0; }}
.cover {{ width:100%; height:100%; object-fit:cover; }}
.pill {{ display:inline-block; padding:12px 28px; border-radius:999px; font-family:'Montserrat';
         font-weight:700; letter-spacing:4px; font-size:24px; text-transform:uppercase; }}
.grad-text {{ background:linear-gradient(100deg,#951b81 0%,#951b81 45%,#56c2e3 100%);
              -webkit-background-clip:text; background-clip:text; color:transparent; }}
.barra {{ width:120px; height:8px; border-radius:8px; background:linear-gradient(90deg,#951b81,#56c2e3); }}
.pagina {{ position:absolute; bottom:56px; right:72px; font-family:'Montserrat'; font-weight:600;
           font-size:22px; letter-spacing:3px; }}
/* motivo de marca: cápsula en degradé con círculo blanco */
.capsula {{ position:absolute; width:300px; height:760px; border-radius:150px; background:var(--deg); }}
.capsula::after {{ content:''; position:absolute; left:28px; bottom:28px; width:244px; height:244px;
                   border-radius:50%; background:#fff; }}
/* motivo de marca: paralelogramos inclinados */
.slash {{ position:absolute; width:150px; height:520px; border-radius:30px; transform:skewX(-33deg);
          background:linear-gradient(200deg,#56c2e3 0%,#56c2e3 40%,#951b81 100%); }}
"""


def pagina(n, oscuro=False):
    color = "rgba(255,255,255,.85)" if oscuro else "#951b81"
    return f'<div class="pagina" style="color:{color}">0{n} / 06</div>'


SLIDES = []

# 1 · PORTADA
SLIDES.append(f"""
<div class="full"><img class="cover" src="{A}/fotos/grupo_vertical.jpg" style="object-position:50% 70%; transform:scale(1.04)"></div>
<div class="full" style="background:linear-gradient(180deg, rgba(29,29,27,.55) 0%, rgba(29,29,27,0) 22%, rgba(29,29,27,0) 45%, rgba(60,10,52,.82) 72%, rgba(80,12,70,.97) 100%)"></div>
<img src="{A}/logo_horizontal_negativo.png" style="position:absolute; top:60px; left:72px; width:430px">
<div style="position:absolute; left:72px; right:72px; bottom:150px; color:#fff">
  <span class="pill" style="background:var(--celeste); color:#fff">Cierre de año 2026</span>
  <h1 class="mont" style="font-weight:800; font-size:86px; line-height:1.02; margin-top:30px; letter-spacing:-1px">
    Celebramos<br>el fin de año con<br><span style="color:var(--celeste)">Grupo San Cristóbal</span>
  </h1>
</div>
""")

# 3 · COLLAGE BRINDIS
SLIDES.append(f"""
<div class="full" style="background:var(--negro)"></div>
<div style="position:absolute; top:0; left:0; width:534px; height:1350px; overflow:hidden">
  <img class="cover" src="{A}/fotos/brindis.jpg" style="object-position:62% 50%"></div>
<div style="position:absolute; top:0; right:0; width:534px; height:1350px; overflow:hidden">
  <img class="cover" src="{A}/fotos/discurso_2.jpg" style="object-position:55% 50%"></div>
<div class="full" style="background:linear-gradient(180deg, rgba(29,29,27,0) 50%, rgba(29,29,27,.65) 70%, rgba(29,29,27,.95) 100%)"></div>
<div style="position:absolute; left:72px; right:72px; bottom:140px; color:#fff">
  <div class="barra" style="background:var(--celeste)"></div>
  <h2 class="mont" style="font-weight:800; font-size:76px; line-height:1.05; margin-top:30px">
    Palabras, brindis<br>y <span style="color:var(--celeste)">gratitud</span></h2>
  <p style="font-size:32px; line-height:1.45; margin-top:22px; opacity:.92">Una noche para mirar todo lo recorrido juntos.</p>
</div>
""")

# 4 · DISCURSO + FRASE
SLIDES.append(f"""
<div style="position:absolute; top:0; left:0; right:0; height:820px; overflow:hidden">
  <img class="cover" src="{A}/fotos/discurso_1.jpg" style="object-position:40% 45%"></div>
<div style="position:absolute; top:770px; left:0; right:0; bottom:0; background:#fff; border-radius:56px 56px 0 0"></div>
<div class="slash" style="right:-60px; top:690px; width:110px; height:260px; border-radius:24px"></div>
<div style="position:absolute; left:80px; right:160px; top:840px">
  <div class="mont grad-text" style="font-weight:800; font-size:150px; line-height:.6; height:70px">“</div>
  <h2 class="mont" style="font-weight:700; font-size:66px; line-height:1.12; margin-top:16px">
    ¡Celebremos juntos todo lo que construimos en 2026!</h2>
  <p class="mont" style="font-weight:600; font-size:26px; letter-spacing:3px; margin-top:36px; color:var(--violeta)">FIN DE AÑO · GRUPO SAN CRISTÓBAL</p>
</div>
""")

# 5 · FOTO GRUPAL
SLIDES.append(f"""
<div class="full" style="background:linear-gradient(160deg,#56c2e3 0%,#7a5fa8 30%,#951b81 62%,#6d1360 100%)"></div>
<div style="position:absolute; left:60px; right:60px; top:150px; height:720px; border-radius:40px; overflow:hidden; box-shadow:0 30px 60px rgba(0,0,0,.35); border:10px solid #fff">
  <img class="cover" src="{A}/fotos/grupo_horizontal.jpg" style="object-position:50% 62%"></div>
<div style="position:absolute; left:80px; right:80px; top:940px; color:#fff">
  <h2 class="mont" style="font-weight:800; font-size:68px; line-height:1.08">Gracias por la invitación<br>y por tanto compartido</h2>
  <p style="font-size:32px; line-height:1.45; margin-top:24px; opacity:.95">Detrás de cada logro hay un equipo que trabaja codo a codo.</p>
</div>
""")


RENDER_JS = """
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1080, height: 1350 } });
  for (const [html, png] of JSON.parse(process.argv[1])) {
    await pg.goto('file://' + html, { waitUntil: 'networkidle' });
    await pg.evaluate(() => document.fonts.ready);
    await pg.waitForTimeout(300);
    await pg.screenshot({ path: png });
  }
  await b.close();
})();
"""


def main():
    import json
    pares = []
    for i, body in enumerate(SLIDES, 1):
        html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"
        f = OUT / f"_slide{i}.html"
        f.write_text(html, encoding="utf-8")
        pares.append([str(f), str(OUT / f"san_cristobal_0{i}.png")])
    subprocess.run(["node", "-e", RENDER_JS, json.dumps(pares)], check=True)
    for h, _ in pares:
        Path(h).unlink()
    print("listo:", len(pares), "placas en", OUT)


if __name__ == "__main__":
    main()
