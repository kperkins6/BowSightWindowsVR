"""Read only the TES4/WEAP/STAT records needed for bow discovery.

Layout reference: TES5Edit Core/wbDefinitionsTES5.pas (WEAP DNAM/WNAM/CNAM).
Form identities use origin plugin names, never load-order-dependent runtime IDs.
"""
from pathlib import Path
import struct
import zlib

LIMIT = 32 * 1024 * 1024


def inflate(data, expected):
    if not 0 <= expected <= LIMIT:
        raise ValueError('Oversized compressed record/asset')
    decoder = zlib.decompressobj()
    result = decoder.decompress(data, expected + 1)
    if len(result) != expected or not decoder.eof or decoder.unconsumed_tail:
        raise ValueError('Compressed size mismatch')
    return result


def subrecords(data):
    pos = 0
    fields = {}
    extended = None
    while pos < len(data):
        if pos + 6 > len(data):
            raise ValueError('Truncated subrecord')
        tag, size = struct.unpack_from('<4sH', data, pos)
        pos += 6
        if tag == b'XXXX':
            if size != 4 or pos + 4 > len(data) or extended is not None:
                raise ValueError('Invalid extended subrecord')
            extended = struct.unpack_from('<I', data, pos)[0]
            pos += 4
            continue
        size = extended if extended is not None else size
        extended = None
        if pos + size > len(data):
            raise ValueError('Subrecord exceeds record')
        fields.setdefault(tag.decode('ascii'), []).append(data[pos:pos+size])
        pos += size
    if extended is not None:
        raise ValueError('Dangling extended subrecord')
    return fields


def records(path):
    with Path(path).open('rb') as f:
        def walk(end, depth=0):
            if depth > 32:
                raise ValueError('Excessive plugin group depth')
            while f.tell() < end:
                start = f.tell()
                h = f.read(24)
                if len(h) != 24:
                    raise ValueError('Truncated plugin header')
                kind = h[:4]
                size, flags, fid = struct.unpack_from('<III', h, 4)
                if kind == b'GRUP':
                    if size < 24 or start + size > end:
                        raise ValueError('Invalid plugin group size')
                    if struct.unpack_from('<I', h, 12)[0] == 0 and h[8:12] not in (b'WEAP', b'STAT'):
                        f.seek(start + size)
                    else:
                        yield from walk(start + size, depth + 1)
                else:
                    if start + 24 + size > end:
                        raise ValueError('Record exceeds plugin group')
                    if kind in (b'TES4', b'WEAP', b'STAT'):
                        if size > LIMIT:
                            raise ValueError('Oversized plugin record')
                        data = f.read(size)
                        if flags & 0x40000:
                            if len(data) < 4: raise ValueError('Missing compressed size')
                            data = inflate(data[4:], struct.unpack_from('<I', data)[0])
                        yield kind.decode('ascii'), flags, fid, subrecords(data)
                    else:
                        f.seek(size, 1)
            if f.tell() != end:
                raise ValueError('Plugin group alignment error')
        yield from walk(Path(path).stat().st_size)


def text(value):
    return value.rstrip(b'\0').decode('utf-8', errors='replace')


def discover_bows(plugins, progress=None, warnings=None):
    warnings=warnings if warnings is not None else []
    graph = {}
    for num, path in enumerate(plugins):
        path = Path(path)
        if progress: progress(f'Reading plugin {num+1}/{len(plugins)}: {path.name}')
        stream = iter(records(path))
        header = next(stream, None)
        if not header or header[0] != 'TES4':
            raise ValueError(f'{path.name}: missing TES4 header')
        origins = [text(m).lower() for m in header[3].get('MAST', [])] + [path.name.lower()]
        def ref(fid):
            if not fid: return None
            index = fid >> 24
            if index >= len(origins):
                raise ValueError(f'{path.name}: invalid local form reference {fid:08X}')
            return origins[index], fid & 0xffffff
        for kind, flags, fid, fields in stream:
            row = dict(kind=kind, deleted=bool(flags & 0x20), provider=path.name,
                       editor=text(fields.get('EDID', [b''])[0]), identity=ref(fid))
            for tag, field in (('MODL','model'), ('DNAM','type'), ('WNAM','first'), ('CNAM','template')):
                if tag not in fields: continue
                value = fields[tag][0]
                if field == 'model': row[field] = text(value).replace('\\','/').lower()
                elif field == 'type':
                    if not value: raise ValueError(f'{path.name}: empty DNAM')
                    row[field] = value[0]
                else:
                    if len(value) != 4: raise ValueError(f'{path.name}: invalid {tag}')
                    row[field] = ref(struct.unpack('<I',value)[0])
            graph[row['identity']] = row
    cache = {}
    def resolved(key, trail=()):
        if key in cache: return cache[key]
        if key in trail or len(trail) > 32: raise ValueError('Cyclic weapon template')
        row = graph.get(key)
        if not row or row['deleted']: return {}
        result = dict(row)
        if row.get('template'):
            if row['template'] not in graph or graph[row['template']]['deleted']:
                warnings.append(f'Unresolved weapon template: {row["identity"]} -> {row["template"]}')
            parent = resolved(row['template'], trail + (key,))
            # WEAP CNAM has no NPC-style template-use mask. Explicit child
            # model/animation/first-person fields take precedence over fallback.
            for field in ('model','type','first'):
                if field not in result and field in parent: result[field] = parent[field]
        cache[key] = result
        return result
    bows = []
    for key, item in graph.items():
        if item['kind'] != 'WEAP' or item['deleted']: continue
        row = resolved(key)
        if row.get('type') != 7: continue
        row = dict(row)
        first = graph.get(row.get('first'), {})
        if row.get('first') and (not first or first.get('deleted') or first.get('kind')!='STAT'):
            warnings.append(f'Unresolved first-person STAT for {row["id"] if "id" in row else key}')
        row['firstPersonModel'] = first.get('model') if not first.get('deleted') and first.get('kind') == 'STAT' else None
        row['id'] = f'{key[0]}:{key[1]:06X}'
        bows.append(row)
    return bows
