# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, "app")

GRAD = ((0x4D, 0xA3, 0xFF), (0x3D, 0xD9, 0xF0), (0x9D, 0x8B, 0xFF))
GRAD_POS = (0.0, 0.48, 1.0)

MARINHO = (0x0C, 0x1A, 0x38)

LADO = 1024
ESCALA = LADO / 256.0


def _fonte(px):
    from PIL import ImageFont

    candidatos = []
    for raiz in (os.environ.get("LOCALAPPDATA"), os.environ.get("SystemRoot")):
        if not raiz:
            continue
        candidatos.append(os.path.join(raiz, "Microsoft", "Windows", "Fonts",
                                       "Inter-Bold.ttf"))
        candidatos.append(os.path.join(raiz, "Fonts", "Inter-Bold.ttf"))
        candidatos.append(os.path.join(raiz, "Fonts", "segoeuib.ttf"))
    for c in candidatos:
        try:
            if os.path.isfile(c):
                return ImageFont.truetype(c, px), os.path.basename(c)
        except Exception:
            pass
    raise RuntimeError("nao achei Inter-Bold nem segoeuib.ttf")


def _faixa_gradiente(lado):
    from PIL import Image

    img = Image.new("RGB", (lado, 1))
    px = img.load()
    for x in range(lado):
        t = x / max(lado - 1, 1)
        for i in range(len(GRAD_POS) - 1):
            a, b = GRAD_POS[i], GRAD_POS[i + 1]
            if a <= t <= b:
                k = (t - a) / max(b - a, 1e-9)
                c0, c1 = GRAD[i], GRAD[i + 1]
                px[x, 0] = tuple(int(round(c0[j] + (c1[j] - c0[j]) * k))
                                 for j in range(3))
                break
    return img.resize((lado, lado))


def desenhar():
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, LADO - 1, LADO - 1],
                        radius=int(58 * ESCALA), fill=MARINHO + (255,))

    TEXTO = u".ai"
    px = 620
    fonte, nome_fonte = _fonte(px)
    tracking = int(round(-0.028 * px))

    def _medir(f, tr):
        larg = 0
        alturas = []
        for i, ch in enumerate(TEXTO):
            cx = d.textbbox((0, 0), ch, font=f)
            larg += (cx[2] - cx[0]) if i == len(TEXTO) - 1 else \
                    (f.getlength(ch) + tr)
            alturas.append(cx)
        return larg, alturas

    alvo = LADO * 0.74
    for _ in range(40):
        larg, _a = _medir(fonte, tracking)
        if abs(larg - alvo) < LADO * 0.01:
            break
        px = int(px * (alvo / max(larg, 1)))
        fonte, nome_fonte = _fonte(px)
        tracking = int(round(-0.028 * px))
    larg, _a = _medir(fonte, tracking)

    mask = Image.new("L", (LADO, LADO), 0)
    dm = ImageDraw.Draw(mask)
    caixa = dm.textbbox((0, 0), TEXTO, font=fonte)
    x = (LADO - larg) / 2.0
    y = (LADO - (caixa[3] - caixa[1])) / 2.0 - caixa[1]
    for ch in TEXTO:
        dm.text((x, y), ch, font=fonte, fill=255)
        x += fonte.getlength(ch) + tracking

    faixa = _faixa_gradiente(LADO).convert("RGBA")
    img.paste(faixa, (0, 0), mask)
    return img, nome_fonte


def _caminho_da_fonte():
    for raiz in (os.environ.get("LOCALAPPDATA"), os.environ.get("SystemRoot")):
        if not raiz:
            continue
        for c in (os.path.join(raiz, "Microsoft", "Windows", "Fonts",
                               "Inter-Bold.ttf"),
                  os.path.join(raiz, "Fonts", "Inter-Bold.ttf"),
                  os.path.join(raiz, "Fonts", "segoeuib.ttf")):
            if os.path.isfile(c):
                return c
    raise RuntimeError("nao achei Inter-Bold nem segoeuib.ttf")


def desenhar_svg():
    from fontTools.ttLib import TTFont
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.boundsPen import BoundsPen

    arquivo = _caminho_da_fonte()
    f = TTFont(arquivo)
    gs = f.getGlyphSet()
    cmap = f.getBestCmap()
    upm = float(f["head"].unitsPerEm)
    track = -0.028 * upm

    itens, x = [], 0.0
    for ch in u".ai":
        nome = cmap[ord(ch)]
        g = gs[nome]
        bp = BoundsPen(gs)
        g.draw(bp)
        pen = SVGPathPen(gs)
        g.draw(pen)
        itens.append((x, bp.bounds, pen.getCommands()))
        x += g.width + track

    x0 = min(ox + b[0] for ox, b, _d in itens)
    x1 = max(ox + b[2] for ox, b, _d in itens)
    y0 = min(b[1] for _ox, b, _d in itens)
    y1 = max(b[3] for _ox, b, _d in itens)
    s = 256.0 * 0.74 / (x1 - x0)
    tx = (256.0 - (x1 - x0) * s) / 2.0 - x0 * s
    ty = (256.0 + (y1 - y0) * s) / 2.0 + y0 * s

    from fontTools.pens.transformPen import TransformPen
    caminhos = []
    for (ox, _b, _d), ch in zip(itens, u".ai"):
        pen = SVGPathPen(gs, ntos=lambda v: (u"%.2f" % v).rstrip(u"0").rstrip(u"."))
        gs[cmap[ord(ch)]].draw(TransformPen(pen, (s, 0, 0, -s, tx + ox * s, ty)))
        caminhos.append(u'  <path d="%s"/>' % pen.getCommands())

    cor = lambda c: u"#%02X%02X%02X" % c
    return u"\n".join([
        u'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" '
        u'width="256" height="256" role="img" aria-label=".ai">',
        u'  <!-- Gerado por build/gerar_icone.py a partir de %s. Nao edite a'
        u' mao:' % os.path.basename(arquivo),
        u'       o .ico, o .png e este .svg sao o MESMO desenho, e so '
        u'continuam',
        u'       sendo se sairem do mesmo script. -->',
        u'  <defs>',
        u'    <linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" '
        u'y1="0" x2="256" y2="0">',
    ] + [u'      <stop offset="%g" stop-color="%s"/>' % (p, cor(c))
         for p, c in zip(GRAD_POS, GRAD)] + [
        u'    </linearGradient>',
        u'  </defs>',
        u'  <rect width="256" height="256" rx="58" fill="%s"/>' % cor(MARINHO),
        u'  <g fill="url(#g)">',
    ] + caminhos + [u'  </g>', u'</svg>', u""])


def main():
    try:
        from PIL import Image
    except ImportError:
        print(u"PAREI: este script precisa do Pillow.\n"
              u"  Rode com o Python do bundle (3.10), que o tem.")
        return 1

    grande, nome_fonte = desenhar()

    TAMANHOS = [16, 20, 24, 32, 48, 64, 128, 256]
    ico = os.path.join(DESTINO, "favicon.ico")
    grande.resize((256, 256), Image.LANCZOS).save(
        ico, format="ICO", sizes=[(n, n) for n in TAMANHOS])

    png = os.path.join(DESTINO, "favicon.png")
    grande.resize((256, 256), Image.LANCZOS).save(png, format="PNG")

    svg = os.path.join(DESTINO, "favicon.svg")
    try:
        texto = desenhar_svg()
    except ImportError:
        print(u"PAREI no SVG: falta o fontTools. Rode com o Python do bundle.")
        return 1
    with open(svg, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(texto)

    print(u"fonte usada : %s" % nome_fonte)
    print(u"favicon.svg  %6d bytes  (curvas da fonte)" % os.path.getsize(svg))
    print(u"favicon.ico  %6d bytes  (%s)"
          % (os.path.getsize(ico), u", ".join(str(n) for n in TAMANHOS)))
    print(u"favicon.png  %6d bytes  (256x256)" % os.path.getsize(png))
    return 0


if __name__ == "__main__":
    sys.exit(main())
