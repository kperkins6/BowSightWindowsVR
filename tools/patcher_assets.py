"""Read-only winning loose/BSA asset resolution. Roots are low to high priority."""
from pathlib import Path, PurePosixPath
import os
import struct
from patcher_records import inflate

MAX_ASSET = 16 * 1024 * 1024
MARKER = 'bow-sight-manifest.json'


def asset_path(value):
    value = str(value).replace('\\', '/')
    p = PurePosixPath(value)
    if not value or value.startswith('/') or ':' in value or '\0' in value or any(q in ('..','.') for q in value.split('/')):
        raise ValueError(f'Unsafe asset path: {value}')
    return p.as_posix().lower()


def find_file(root, relative):
    p = Path(root) / asset_path(relative)
    if p.is_file(): return p
    if os.name == 'nt': return None
    # Windows is case insensitive; this fallback also supports Linux tests.
    p = Path(root)
    for part in asset_path(relative).split('/'):
        if not p.is_dir(): return None
        p = next((c for c in p.iterdir() if c.name.lower() == part), None)
        if p is None: return None
    return p if p.is_file() else None


def lz4_block(src, expected):
    if expected > MAX_ASSET: raise ValueError('Oversized LZ4 asset')
    out = bytearray(); pos = 0
    def length(n):
        nonlocal pos
        if n == 15:
            while True:
                if pos >= len(src): raise ValueError('Truncated LZ4 length')
                b=src[pos];pos+=1;n+=b
                if b != 255: break
        return n
    while pos < len(src):
        token=src[pos];pos+=1;n=length(token>>4)
        if pos+n>len(src) or len(out)+n>expected: raise ValueError('Invalid LZ4 literal')
        out.extend(src[pos:pos+n]);pos+=n
        if pos==len(src): break
        if pos+2>len(src): raise ValueError('Truncated LZ4 match')
        offset=int.from_bytes(src[pos:pos+2],'little');pos+=2;n=length(token&15)+4
        if not 0<offset<=len(out) or len(out)+n>expected: raise ValueError('Invalid LZ4 match')
        for _ in range(n): out.append(out[-offset])
    if len(out)!=expected: raise ValueError('LZ4 size mismatch')
    return bytes(out)


class BSA:
    def __init__(self, path):
        self.path=Path(path); self.entries={}
        with self.path.open('rb') as f:
            def unpack(fmt):
                n=struct.calcsize(fmt);b=f.read(n)
                if len(b)!=n: raise ValueError('Truncated BSA index')
                return struct.unpack(fmt,b)
            magic,self.version,offset,self.flags,nfolders,nfiles,flen,nlen,_=unpack('<4s8I')
            if magic!=b'BSA\0' or self.version not in (104,105) or self.flags&3!=3:
                raise ValueError('Unsupported BSA header/names')
            if nfiles>2_000_000 or nfolders>200_000 or nlen>128*1024*1024:
                raise ValueError('Oversized BSA index')
            f.seek(offset)
            counts=[unpack('<QIIQ' if self.version==105 else '<QII')[1] for _ in range(nfolders)]
            if sum(counts)!=nfiles: raise ValueError('BSA folder/file count mismatch')
            entries=[]
            for count in counts:
                n=unpack('<B')[0];folder=f.read(n).rstrip(b'\0').decode('cp1252')
                for _ in range(count):
                    _,size,start=unpack('<QII');entries.append((folder,size,start))
            names=f.read(nlen).split(b'\0', nfiles)[:nfiles]
            if len(names)!=nfiles or any(not n for n in names): raise ValueError('BSA filename count mismatch')
            for (folder,size,start),name in zip(entries,names):
                if not name.lower().endswith(b'.nif'): continue
                key=asset_path(folder+'/'+name.decode('cp1252'))
                self.entries[key]=(size,start)

    def read(self, key):
        size,start=self.entries[asset_path(key)]
        compressed=bool(self.flags&4)^bool(size&0x40000000);size&=0x3fffffff
        if size>MAX_ASSET+4096: raise ValueError('Oversized BSA asset')
        with self.path.open('rb') as f: f.seek(start);data=f.read(size)
        if len(data)!=size: raise ValueError('Truncated BSA asset')
        if self.flags&0x100:
            if not data or 1+data[0]>len(data): raise ValueError('Invalid embedded BSA filename')
            data=data[1+data[0]:]
        if compressed:
            if len(data)<4: raise ValueError('Missing BSA uncompressed size')
            expected=struct.unpack_from('<I',data)[0]
            if expected>MAX_ASSET: raise ValueError('Oversized decompressed mesh')
            data=inflate(data[4:],expected) if self.version==104 else lz4_block(data[4:],expected)
        return data


class AssetIndex:
    def __init__(self, roots, plugins, ini_archives=(), progress=None):
        self.roots=[Path(p).resolve() for p in roots];self.archives=[];self.warnings=[];self.loose={}
        available={}
        for root in self.roots:
            if root.is_dir():
                for p in root.iterdir():
                    if p.is_file() and p.suffix.lower()=='.bsa': available[p.name.lower()]=p
                mesh_dir=root/'meshes'
                if mesh_dir.is_dir():
                    if progress: progress('Indexing loose meshes: '+root.name)
                    for directory,_,files in os.walk(mesh_dir):
                        for name in files:
                            if name.lower().endswith('.nif'):
                                p=Path(directory)/name
                                self.loose[p.relative_to(root).as_posix().lower()]=p
        names=[]
        # Explicit INI order takes precedence; fallback standard game archives
        # are used only when no effective archive INI was supplied.
        if ini_archives:
            names.extend(str(n).lower() for n in ini_archives)
        else:
            names.extend(sorted(n for n in available if n.startswith(('skyrim -','skyrim_vr -'))))
        for plugin in plugins:
            stem=Path(plugin).stem.lower()
            names.extend(sorted(n for n in available if n==stem+'.bsa' or n.startswith(stem+' - ')))
        for name in dict.fromkeys(names):
            p=available.get(name)
            if not p:
                self.warnings.append('Configured archive missing: '+name);continue
            if progress: progress('Indexing archive: '+p.name)
            try: self.archives.append(BSA(p))
            except (ValueError,OSError,struct.error,UnicodeError) as e:
                raise ValueError(f'Cannot resolve archive {p.name}: {e}') from e

    def locate(self, key):
        key=asset_path(key)
        if key in self.loose: return self.loose[key],None
        for archive in reversed(self.archives):
            if key in archive.entries: return archive,key
        raise FileNotFoundError('Mesh not found in active assets: '+key)

    def read(self, key):
        source,entry=self.locate(key)
        if entry is None:
            if source.stat().st_size>MAX_ASSET: raise ValueError('Oversized loose mesh')
            return source.read_bytes(),str(source)
        return source.read(entry),str(source.path)+' :: '+entry

    def exists(self,key):
        try: self.locate(key);return True
        except FileNotFoundError: return False
