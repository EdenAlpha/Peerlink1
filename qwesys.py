from __future__ import annotations
from pathlib import Path
import struct,zlib

def read(path):
    d=Path(path).read_bytes()
    if d[:8]!=b'\xff QWESYS': raise ValueError('not QWESYS')
    comp,rawsz=struct.unpack_from('<II',d,8);raw=zlib.decompress(d[16:])
    if len(raw)!=rawsz: raise ValueError('size mismatch')
    n,table=struct.unpack_from('<II',raw,0);out={}
    for i in range(n):
        off,size,nameoff=struct.unpack_from('<III',raw,table+i*12)
        e=raw.index(0,nameoff);name=raw[nameoff:e].decode()
        out[name]=raw[off:off+size]
    return out
