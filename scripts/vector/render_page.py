import sys, os, fitz
sys.path.insert(0, os.path.dirname(__file__))
from vecutil import *
pno = int(sys.argv[1]); x0, y0, x1, y1 = map(float, sys.argv[2:6]); zoom = float(sys.argv[6])
pix = doc()[pno - 1].get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=fitz.Rect(x0, y0, x1, y1))
pix.save(os.path.join(OUT, sys.argv[7]))
