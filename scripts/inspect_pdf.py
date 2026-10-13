import sys, os, fitz
src, outdir = sys.argv[1], sys.argv[2]
os.makedirs(outdir, exist_ok=True)
doc = fitz.open(src)
log = open(os.path.join(outdir, "info.txt"), "w", encoding="utf-8")
log.write(f"pages {len(doc)}\n")
thumbs = []
for i, p in enumerate(doc):
    t = " ".join(p.get_text().split())[:200]
    log.write(f"p{i+1} | {t}\n")
    thumbs.append(p.get_pixmap(dpi=18, alpha=False))
log.close()
W, H = thumbs[0].width, thumbs[0].height
cols, rows = 4, 3
n = cols * rows
for s in range(0, len(thumbs), n):
    sheet = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, cols * W, rows * H), False)
    sheet.set_rect(sheet.irect, (255, 255, 255))
    for k, pix in enumerate(thumbs[s:s + n]):
        pix.set_origin((k % cols) * W, (k // cols) * H)
        sheet.copy(pix, pix.irect)
    sheet.save(os.path.join(outdir, f"sheet_p{s+1:03d}.png"))
print("ok")
