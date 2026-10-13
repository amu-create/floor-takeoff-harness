import os, pathlib
"""Shared helpers: load drawings per layer and rasterize them with OpenCV."""
import fitz, numpy as np, cv2, os
ROOT = os.environ.get("CONPA_ROOT", str(pathlib.Path(__file__).resolve().parents[2]))
PDF = os.path.join(ROOT, "data", "raw_kba", "plan.pdf")
OUT = os.path.join(ROOT, "out")
_doc = None


def doc():
    global _doc
    if _doc is None:
        _doc = fitz.open(PDF)
    return _doc


def bez(p0, p1, p2, p3, n=12):
    t = np.linspace(0, 1, n)[:, None]
    P = [np.array([p.x, p.y]) for p in (p0, p1, p2, p3)]
    return ((1 - t) ** 3) * P[0] + 3 * ((1 - t) ** 2) * t * P[1] + 3 * (1 - t) * t * t * P[2] + (t ** 3) * P[3]


def polylines(it):
    """Yield list of Nx2 arrays (pdf pt) for one drawing item."""
    out = []
    for x in it["items"]:
        op = x[0]
        if op == "l":
            out.append(np.array([[x[1].x, x[1].y], [x[2].x, x[2].y]]))
        elif op == "c":
            out.append(bez(x[1], x[2], x[3], x[4]))
        elif op == "re":
            r = x[1]
            out.append(np.array([[r.x0, r.y0], [r.x1, r.y0], [r.x1, r.y1], [r.x0, r.y1], [r.x0, r.y0]]))
        elif op == "qu":
            q = x[1]
            out.append(np.array([[q.ul.x, q.ul.y], [q.ur.x, q.ur.y], [q.lr.x, q.lr.y], [q.ll.x, q.ll.y], [q.ul.x, q.ul.y]]))
    return out


def get_drawings(pno):
    return doc()[pno - 1].get_drawings()


def raster(drawings, layers, clip, ppt, thick=1, img=None, color=255, min_len=0.0):
    """Draw selected layers into a uint8 mask. clip=(x0,y0,x1,y1) pt, ppt=pixels per pt."""
    x0, y0, x1, y1 = clip
    W, H = int((x1 - x0) * ppt) + 1, int((y1 - y0) * ppt) + 1
    if img is None:
        img = np.zeros((H, W), np.uint8)
    for it in drawings:
        if layers is not None and it.get("layer") not in layers:
            continue
        for pl in polylines(it):
            if min_len and np.abs(np.diff(pl, axis=0)).sum() < min_len:
                continue
            pts = np.round((pl - [x0, y0]) * ppt * 8).astype(np.int32)
            cv2.polylines(img, [pts], False, color, thick, cv2.LINE_8, shift=3)
    return img


def spans(pno):
    p = doc()[pno - 1]
    res = []
    for b in p.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            for sp in l["spans"]:
                t = sp["text"].strip()
                if t:
                    res.append(dict(text=t, bbox=tuple(sp["bbox"]), size=sp["size"]))
    return res


def imwrite(path, img):
    """cv2.imwrite cannot handle non-ASCII paths on Windows."""
    ok, buf = cv2.imencode(os.path.splitext(path)[1], img)
    buf.tofile(path)
