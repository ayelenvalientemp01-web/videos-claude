"""Recorta los logos de las capturas del manual de marca y les quita el fondo blanco."""
from PIL import Image
import numpy as np

U = "/root/.claude/uploads/d178f4de-cb43-53ef-8795-f1e6ce727ffd/"
CORTES = {
    "isotipo": ("ed82355b-image.png", (120, 990, 1110, 1980)),
    "logo_vertical": ("d97a9679-image.png", (120, 730, 1190, 1270)),
    "logo_horizontal": ("d97a9679-image.png", (110, 1580, 1210, 1835)),
}

def sin_fondo(im):
    a = np.asarray(im.convert("RGB")).astype(float)
    mn = a.min(axis=2)
    alpha = np.clip((250 - mn) / 45.0, 0, 1)
    rgba = np.dstack([a, alpha * 255]).astype(np.uint8)
    out = Image.fromarray(rgba, "RGBA")
    return out.crop(out.getbbox())

for nombre, (f, box) in CORTES.items():
    im = sin_fondo(Image.open(U + f).crop(box))
    im.save(f"assets/{nombre}.png")
    # versión blanca para fondos oscuros / fotos
    blanco = Image.new("RGBA", im.size, (255, 255, 255, 0))
    blanco.putalpha(im.getchannel("A"))
    w = Image.new("RGBA", im.size, (255, 255, 255, 255)); w.putalpha(im.getchannel("A"))
    w.save(f"assets/{nombre}_blanco.png")
    print(nombre, im.size)

# Versión "negativo": isotipo en degradé + texto en blanco (para fondos oscuros)
for nombre in ["logo_horizontal", "logo_vertical"]:
    im = Image.open(f"assets/{nombre}.png")
    a = np.asarray(im).copy()
    rgb = a[..., :3].astype(int)
    gris = (rgb.max(axis=2) - rgb.min(axis=2)) < 45
    a[gris, :3] = 255
    Image.fromarray(a, "RGBA").save(f"assets/{nombre}_negativo.png")
