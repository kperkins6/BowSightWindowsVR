"""Synthetic mod lists exercise discovery without distributing game files."""
import json
from pathlib import Path
import struct
import sys
import unittest
import zlib
import hashlib
import os
import http.client
import threading

from test_tools import fixture_dir, FakePart
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))


def sub(tag, data):
    return tag.encode() + struct.pack('<H', len(data)) + data


def record(kind, fid=0, fields=b'', flags=0):
    return kind.encode() + struct.pack('<IIIHHHH', len(fields), flags, fid, 0, 0, 44, 0) + fields


def plugin(path, rows, masters=()):
    header = record('TES4', fields=b''.join(sub('MAST', m.encode()+b'\0') for m in masters))
    path.write_bytes(header + b''.join(rows))


def weapon(fid, name, model, kind=7, **kwargs):
    fields = sub('EDID', name.encode()+b'\0') + sub('DNAM', bytes([kind])+b'\0'*99)
    if model: fields += sub('MODL', model.encode()+b'\0')
    if 'first' in kwargs: fields += sub('WNAM', struct.pack('<I', kwargs['first']))
    if 'template' in kwargs: fields += sub('CNAM', struct.pack('<I', kwargs['template']))
    return record('WEAP', fid, fields, kwargs.get('flags', 0))


def make_bsa(path, payload=b'hello', version=105, compressed=False, toggle=False, embedded=False):
    folder = b'meshes\\weapons\0'; name = b'bow.nif\0'
    flags = 3 | (4 if compressed else 0) | (0x100 if embedded else 0)
    data = payload
    if compressed ^ toggle:
        data = struct.pack('<I', len(payload)) + (zlib.compress(payload) if version == 104 else bytes([len(payload)<<4])+payload)
    if embedded: data = bytes([3])+b'abc'+data
    folder_record = struct.pack('<QIIQ', 0, 1, 0, 36+24+len(name)) if version == 105 else struct.pack('<QII', 0, 1, 36+16+len(name))
    offset = 36 + len(folder_record) + 1 + len(folder) + 16 + len(name)
    path.write_bytes(struct.pack('<4s8I', b'BSA\0', version, 36, flags, 1, 1, len(folder), len(name), 1)
                     + folder_record + bytes([len(folder)]) + folder
                     + struct.pack('<QII', 0, len(data) | (0x40000000 if toggle else 0), offset) + name + data)


def synthetic_nif(two_shapes=False):
    """A tiny generated bow strip and string, no Bethesda geometry."""
    from nif_mesh import Partition, pack
    desc=10 | (4<<8) | (5<<16) | (6<<20) | (7<<28) | (1<<44)
    p=FakePart();raw=[]
    for v in p.vertices:
        b=bytearray(40);struct.pack_into('<3f',b,0,*v['p']);b[20:28]=bytes([0,128,128,128,128,255,128,128])
        struct.pack_into('<4e',b,28,1,0,0,0);raw.append(b)
    p.raw=raw;p.stride=40;p.desc=desc;p.bones=(0,);p.lod=p.glob=0
    partition=Partition.encode(p)
    pose=pack('13f',0,0,0,1,0,0,0,1,0,0,0,1,1)
    def av(name): return pack('IIiI',name,0,-1,0)+pose+pack('i',-1)
    node=av(0)+(pack('I3iI',3,1,2,6,0) if two_shapes else pack('I2iI',2,1,2,0))
    mid=av(1)+pack('II',0,0)
    shape=av(2)+pack('4fiiiQHHII',0,10,0,30,3,-1,-1,desc,len(p.triangles),len(p.vertices),0,0)
    skin=pack('iiiIi',4,5,0,1,1)
    transform=pack('13f',1,0,0,0,1,0,0,0,1,0,0,0,1)
    skin_data=transform+pack('IB',1,1)+transform+pack('4fH',0,10,0,30,len(p.vertices))+b''.join(pack('Hf',i,1) for i in range(len(p.vertices)))
    kinds=['NiNode','BSTriShape','NiSkinInstance','NiSkinData','NiSkinPartition']
    blocks=[node,mid,shape,skin,skin_data,partition];ids=[0,0,1,2,3,4]
    if two_shapes:
        shape2=bytearray(shape);struct.pack_into('<i',shape2,88,7)
        part2=Partition(partition)
        for b in part2.raw:struct.pack_into('<f',b,8,struct.unpack_from('<f',b,8)[0]-5)
        blocks.extend([bytes(shape2),pack('iiiIi',8,9,0,1,1),skin_data,part2.encode()]);ids.extend([1,2,3,4])
    strings=[b'BowRoot',b'Bow_MidBone',b'BowMesh']
    header=b'Gamebryo File Format, Version 20.2.0.7\n'+pack('IBIII',0x14020007,1,12,len(blocks),100)+b'\0\0\0'+pack('H',len(kinds))
    header+=b''.join(pack('I',len(k))+k.encode() for k in kinds)
    header+=pack('H'*len(ids),*ids)+pack('I'*len(blocks),*[len(b) for b in blocks])+pack('II',3,max(map(len,strings)))
    header+=b''.join(pack('I',len(s))+s for s in strings)+pack('I',0)
    return header+b''.join(blocks)+pack('Ii',1,0)


def project_fixture(folder):
    from patcher_project import Project
    from patcher_scan import scan
    data=Path(folder)/'Data';(data/'meshes/weapons').mkdir(parents=True)
    (data/'meshes/weapons/bow.nif').write_bytes(synthetic_nif())
    plugin(data/'Skyrim.esm',[weapon(1,'TestBow','weapons/bow.nif')])
    plugins=Path(folder)/'plugins.txt';plugins.write_text('*Skyrim.esm\n')
    return Project(scan(dict(mode='data',data=str(data),plugins=str(plugins))))


def mixed_project_fixture(folder):
    from patcher_project import Project
    from patcher_scan import scan
    from nif_mesh import Mesh,assemble
    base=project_fixture(folder);data=Path(folder)/'Data'
    mesh=Mesh(synthetic_nif());d=mesh.parts[0];part=d['part']
    for raw in part.raw:struct.pack_into('<f',raw,4,struct.unpack_from('<f',raw,4)[0]+100)
    (data/'meshes/weapons/no-opening.nif').write_bytes(assemble(mesh.data,{d['partition']:part.encode()}))
    (data/'meshes/weapons/unsupported.nif').write_bytes(b'Unsupported synthetic format')
    plugin(data/'Skyrim.esm',[weapon(1,'GoodBow','weapons/bow.nif'),weapon(2,'NeedsAdjustment','weapons/no-opening.nif'),weapon(3,'Unsupported','weapons/unsupported.nif')])
    return Project(scan(base.inventory['config']))


class DiscoveryTests(unittest.TestCase):
    def test_discovery_is_available(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('patcher_scan'), 'standalone discovery module is missing')

    def test_final_overrides_templates_first_person_and_mod_added_bows(self):
        from patcher_records import discover_bows
        with fixture_dir() as t:
            root=Path(t); base=root/'Skyrim.esm'; mod=root/'Custom.esp'
            plugin(base, [weapon(1,'Base','weapons/base.nif'), weapon(2,'Removed','weapons/remove.nif'), weapon(3,'Deleted','weapons/delete.nif'),
                          record('STAT',4,sub('MODL', b'weapons/first.nif\0'))])
            plugin(mod, [weapon(1,'Replaced','weapons/new.nif',first=4), weapon(2,'NowCrossbow','weapons/cross.nif',kind=9),
                         weapon(3,'Gone','weapons/delete.nif',flags=0x20), weapon(0x1000800,'ModBow','weapons/custom.nif'),
                         record('WEAP',0x1000801, sub('EDID',b'TemplateChild\0')+sub('CNAM',struct.pack('<I',1)))], ['Skyrim.esm'])
            bows=discover_bows([base,mod])
            self.assertEqual({b['editor'] for b in bows}, {'Replaced','ModBow','TemplateChild'})
            child=next(b for b in bows if b['editor']=='TemplateChild')
            self.assertEqual(child['model'],'weapons/new.nif')
            self.assertEqual(child['firstPersonModel'],'weapons/first.nif')
            self.assertEqual(child['provider'],'Custom.esp')

    def test_truncated_and_cyclic_plugin_records_are_refused(self):
        from patcher_records import discover_bows
        with fixture_dir() as t:
            p=Path(t)/'Bad.esp';p.write_bytes(b'GRUP'+struct.pack('<I',0)+b'\0'*16)
            with self.assertRaises(ValueError): discover_bows([p])

    def test_unresolved_first_person_model_produces_diagnostic(self):
        from patcher_records import discover_bows
        with fixture_dir() as t:
            p=Path(t)/'Custom.esp';plugin(p,[weapon(1,'Bow','weapons/bow.nif',first=2)])
            warnings=[];discover_bows([p],warnings=warnings)
            self.assertTrue(any('first-person' in w for w in warnings))

    def test_modlist_change_invalidates_generation(self):
        with fixture_dir() as t:
            project=project_fixture(t);key=project.rows[0]['id'];project.preview(key);project.approve(key)
            (Path(t)/'plugins.txt').write_text('*Skyrim.esm\n# Changed profile\n')
            with self.assertRaisesRegex(ValueError,'changed'): project.generate(Path(t)/'Output')

    def test_bsa_versions_compression_toggle_and_embedded_names(self):
        from patcher_assets import BSA
        with fixture_dir() as t:
            for v in (104,105):
                for compressed,toggle,embedded in ((False,False,False),(True,False,True),(False,True,True),(True,True,False)):
                    p=Path(t)/f'{v}-{compressed}-{toggle}.bsa'
                    make_bsa(p,version=v,compressed=compressed,toggle=toggle,embedded=embedded)
                    self.assertEqual(BSA(p).read('meshes/weapons/bow.nif'), b'hello')

    def test_loose_wins_archive_and_highest_priority_root_wins(self):
        from patcher_assets import AssetIndex
        with fixture_dir() as t:
            roots=[Path(t)/n for n in ('data','low','high')]
            for root in roots: root.mkdir()
            make_bsa(roots[2]/'Custom.bsa',payload=b'archive')
            for root,payload in ((roots[0],b'data loose'),(roots[1],b'low loose')):
                p=root/'meshes/weapons/bow.nif';p.parent.mkdir(parents=True);p.write_bytes(payload)
            ix=AssetIndex(roots,['Custom.esp'])
            data,provider=ix.read('meshes/weapons/bow.nif')
            self.assertEqual(data,b'low loose');self.assertIn('low',provider)

    def test_mo2_reverse_priority_excludes_generated_mod(self):
        from patcher_scan import scan
        with fixture_dir() as t:
            root=Path(t);mo=root/'mo';data=root/'game/Data';data.mkdir(parents=True)
            profile=mo/'profiles/Test';profile.mkdir(parents=True)
            (mo/'ModOrganizer.ini').write_text('[General]\ngamePath='+str(data.parent)+'\nselected_profile=Test\n')
            (profile/'modlist.txt').write_text('+Generated\n+High\n+Low\n')
            (profile/'plugins.txt').write_text('*Skyrim.esm\n')
            (profile/'loadorder.txt').write_text('Skyrim.esm\n')
            for n,payload in (('Low',b'low'),('High',b'high'),('Generated',b'already patched')):
                p=mo/'mods'/n/'meshes/weapons/bow.nif';p.parent.mkdir(parents=True);p.write_bytes(payload)
            (mo/'mods/Generated/bow-sight-manifest.json').write_text('{}')
            plugin(data/'Skyrim.esm',[weapon(1,'Bow','weapons/bow.nif')])
            result=scan(dict(mode='mo2',mo2=str(mo/'ModOrganizer.ini'),profile='Test'))
            self.assertEqual(len(result['bows']),1)
            self.assertIn('High',result['bows'][0]['source'])
            self.assertTrue(any('Generated' in w for w in result['warnings']))

    def test_asset_path_traversal_is_rejected(self):
        from patcher_assets import asset_path
        for value in ('../x.nif','C:/x.nif','/absolute.nif','meshes/../../x.nif','meshes/x:nif'):
            with self.assertRaises(ValueError): asset_path(value)

    def test_bsa_padded_name_table_does_not_become_extra_files(self):
        from patcher_assets import BSA
        with fixture_dir() as t:
            p=Path(t)/'padded.bsa';make_bsa(p)
            data=bytearray(p.read_bytes());struct.pack_into('<I',data,28,13)
            p.write_bytes(data+b'\0'*10)
            self.assertEqual(BSA(p).read('meshes/weapons/bow.nif'),b'hello')

    def test_archive_name_is_not_a_mesh_filter(self):
        from patcher_assets import AssetIndex
        with fixture_dir() as t:
            p=Path(t)/'BowTextureFix.bsa';make_bsa(p)
            ix=AssetIndex([Path(t)],['BowTextureFix.esp'])
            self.assertEqual(ix.read('meshes/weapons/bow.nif')[0],b'hello')


class AdjustableGeometryTests(unittest.TestCase):
    def test_custom_profile_moves_opening_and_preserves_string(self):
        from window import apply_window
        from nif_mesh import identity
        p=FakePart()
        apply_window(dict(part=p,mapping=identity()), 'left', .6,
                     profile=dict(shelf=8.,height=8.,taper=2.,bevel=.2,inner=-1.3,protect_string=True))
        moved=[b for a,b in zip(p.preview_before,p.preview_after) if a!=b]
        self.assertTrue(moved)
        self.assertTrue(all(8 < q[1] < 16 and q[0]>-9 for q in moved))
    def test_invalid_profile_does_not_mutate(self):
        from window import apply_window
        from nif_mesh import identity
        p=FakePart();before=len(p.vertices)
        with self.assertRaises(ValueError):
            apply_window(dict(part=p,mapping=identity()), 'left', 1., profile=dict(height=-1))
        self.assertEqual(len(p.vertices), before)


class ProjectTests(unittest.TestCase):
    def test_defaults_build_separates_success_failures_and_unsupported(self):
        from patcher_project import DEFAULTS
        with fixture_dir() as t:
            project=mixed_project_fixture(t)
            good=next(r for r in project.rows if r['path']=='weapons/bow.nif')
            project.update(good['id'],{'height':12},include=False);project.set_hand('right')
            progress=[];result=project.prepare_defaults(progress.append)
            self.assertEqual(project.hand,'right');self.assertEqual(good['settings'],DEFAULTS)
            self.assertEqual(len(result['successes']),1);self.assertEqual(len(result['failures']),1);self.assertEqual(len(result['unsupported']),1)
            self.assertTrue(good['include']);self.assertFalse(any(r['approved'] for r in project.rows))
            self.assertTrue(all(not r['include'] for r in project.rows if r is not good));self.assertTrue(progress)
            with self.assertRaisesRegex(ValueError,'review'):project.generate(Path(t)/'Unapproved')
            project.approve_defaults(result['id'])
            output=Path(t)/'Output';self.assertEqual(project.generate(output)['count'],1)
            manifest=json.loads((output/'bow-sight-manifest.json').read_text())
            self.assertEqual([r['path'] for r in manifest['meshes']],['weapons/bow.nif'])
            self.assertEqual(len(manifest['skipped']),2)

    def test_defaults_summary_cannot_approve_changed_geometry_or_wrong_run(self):
        with fixture_dir() as t:
            project=project_fixture(t);result=project.prepare_defaults()
            with self.assertRaises(ValueError):project.approve_defaults('wrong-run')
            key=project.rows[0]['id'];project.update(key,{'height':12})
            self.assertFalse(project.summary()['defaultRun']['current'])
            with self.assertRaisesRegex(ValueError,'changed'):project.approve_defaults(result['id'])
            self.assertFalse(project.rows[0]['approved'])
            result=project.prepare_defaults();project.set_hand('right')
            with self.assertRaises(ValueError):project.approve_defaults(result['id'])

    def test_defaults_summary_cannot_silently_include_failed_mesh(self):
        with fixture_dir() as t:
            project=mixed_project_fixture(t);result=project.prepare_defaults()
            failed=result['failures'][0]['id'];project.update(failed,include=True)
            self.assertFalse(project.summary()['defaultRun']['current'])
            with self.assertRaisesRegex(ValueError,'changed'):project.approve_defaults(result['id'])
            self.assertFalse(any(r['approved'] for r in project.rows))

    def test_defaults_approval_rechecks_source_and_requires_success(self):
        with fixture_dir() as t:
            project=project_fixture(t);result=project.prepare_defaults()
            (Path(t)/'Data/meshes/weapons/bow.nif').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'changed'):project.approve_defaults(result['id'])
            self.assertFalse(project.rows[0]['approved'])
            result=project.prepare_defaults()
            self.assertEqual(len(result['successes']),0)
            self.assertEqual(len(result['failures']),1)
            with self.assertRaisesRegex(ValueError,'successful'):project.approve_defaults(result['id'])

    def test_identical_profile_rewrite_does_not_invalidate_review(self):
        with fixture_dir() as t:
            project=project_fixture(t);key=project.rows[0]['id'];project.preview(key);project.approve(key)
            p=Path(t)/'plugins.txt';stamp=p.stat().st_mtime_ns
            os.utime(p,ns=(stamp+10_000_000,stamp+10_000_000))
            result=project.generate(Path(t)/'Output')
            self.assertEqual(result['count'],1)

    def test_mo2_ui_settings_do_not_invalidate_but_resource_paths_do(self):
        from patcher_project import Project
        from patcher_scan import scan
        with fixture_dir() as t:
            project_fixture(t)
            root=Path(t);mo=root/'MO2';profile=mo/'profiles/Test';profile.mkdir(parents=True)
            (mo/'mods').mkdir();(profile/'modlist.txt').write_text('# Empty mod list\n')
            (profile/'plugins.txt').write_text('*Skyrim.esm\n');(profile/'loadorder.txt').write_text('Skyrim.esm\n')
            ini=mo/'ModOrganizer.ini';content='[General]\ngamePath='+str(root)+'\nselected_profile=Test\n'
            ini.write_text(content)
            project=Project(scan(dict(mode='mo2',mo2=str(ini),profile='Test')))
            key=project.rows[0]['id'];project.preview(key);project.approve(key)
            ini.write_text(content+'[Geometry]\nwidth=1200\n')
            self.assertEqual(project.generate(root/'Output')['count'],1)
            other=mo/'OtherMods';other.mkdir()
            ini.write_text(content+'[Settings]\nmod_directory='+str(other)+'\n')
            with self.assertRaisesRegex(ValueError,'changed'):project.generate(root/'Output2')

    def test_new_higher_priority_plugin_requires_rescan(self):
        from patcher_project import Project
        from patcher_scan import scan
        with fixture_dir() as t:
            project_fixture(t)
            root=Path(t);mo=root/'MO2';profile=mo/'profiles/Test';profile.mkdir(parents=True)
            high=mo/'mods/High';high.mkdir(parents=True)
            (profile/'modlist.txt').write_text('+High\n')
            (profile/'plugins.txt').write_text('*Skyrim.esm\n');(profile/'loadorder.txt').write_text('Skyrim.esm\n')
            ini=mo/'ModOrganizer.ini';ini.write_text('[General]\ngamePath='+str(root)+'\nselected_profile=Test\n')
            project=Project(scan(dict(mode='mo2',mo2=str(ini),profile='Test')))
            key=project.rows[0]['id'];project.preview(key);project.approve(key)
            plugin(high/'Skyrim.esm',[weapon(1,'RedirectedBow','weapons/other.nif')])
            with self.assertRaisesRegex(ValueError,'changed'):project.generate(root/'Output')
            self.assertFalse((root/'Output').exists())

    def test_custom_opening_cannot_push_geometry_outside_original_bounds(self):
        from patcher_project import patch,DEFAULTS
        with self.assertRaisesRegex(ValueError,'bound'):
            patch(synthetic_nif(),'weapons/bow.nif','left',{**DEFAULTS,'inner':-1000,'depth':.98})

    def test_batch_settings_and_approval_are_validated_as_a_set(self):
        with fixture_dir() as t:
            project=project_fixture(t);key=project.rows[0]['id']
            with self.assertRaisesRegex(ValueError,'preview'):project.batch([key],'approve')
            project.batch([key],'settings',{'height':12})
            self.assertEqual(project.rows[0]['settings']['height'],12)
            project.preview(key);project.batch([key],'approve')
            self.assertTrue(project.rows[0]['approved'])
            with self.assertRaises(ValueError):project.batch([key,'missing'],'skip')
            self.assertTrue(project.rows[0]['include'])
            project.batch([key],'skip');self.assertFalse(project.rows[0]['include'])
            project.batch([key],'include');self.assertTrue(project.rows[0]['include'])
            self.assertFalse(project.rows[0]['approved'])

    def test_preview_topology_matches_output_for_unchanged_shape(self):
        from patcher_project import patch, DEFAULTS
        from nif_mesh import Mesh
        output,preview=patch(synthetic_nif(two_shapes=True),'weapons/bow.nif','left',DEFAULTS)
        mesh=Mesh(output)
        for d in mesh.parts:
            shape=next(s for s in preview['shapes'] if s['id']==d['shape'])
            self.assertTrue(all(max(t)<len(shape['after']) for t in shape['triangles']))
            self.assertEqual(shape['triangles'],d['part'].triangles)

    def test_new_higher_priority_source_is_detected_at_generation(self):
        with fixture_dir() as t:
            project=project_fixture(t);key=project.rows[0]['id'];project.preview(key);project.approve(key)
            high=Path(t)/'High';high.mkdir();project.inventory['roots'].append(str(high))
            p=high/'meshes/weapons/bow.nif';p.parent.mkdir(parents=True);p.write_bytes(synthetic_nif())
            with self.assertRaisesRegex(ValueError,'changed'):project.generate(Path(t)/'Output')

    def test_zip_suffix_output_is_rejected_before_writing(self):
        with fixture_dir() as t:
            project=project_fixture(t);key=project.rows[0]['id'];project.preview(key);project.approve(key)
            with self.assertRaisesRegex(ValueError,'folder|ZIP'):project.generate(Path(t)/'Output.zip')
            self.assertFalse((Path(t)/'Output.zip').exists())
    def test_preview_approval_changes_and_generation(self):
        from nif_io import blocks
        with fixture_dir() as t:
            project=project_fixture(t);key=project.rows[0]['id']
            preview=project.preview(key)
            self.assertTrue(preview['shapes']);self.assertTrue(preview['changedVertices']>0)
            with self.assertRaisesRegex(ValueError,'review'): project.generate(Path(t)/'unreviewed')
            project.approve(key);project.update(key,dict(depth=.5))
            self.assertFalse(project.rows[0]['approved'])
            project.preview(key);project.approve(key)
            output=Path(t)/'Output';result=project.generate(output)
            patched=(output/'meshes/weapons/bow.nif').read_bytes()
            self.assertEqual(result['count'],1)
            self.assertTrue((output/'bow-sight-manifest.json').exists())
            self.assertTrue(output.with_suffix('.zip').is_file())
            for i in (0,1,2,3): self.assertEqual(blocks(patched)[i][2],blocks(synthetic_nif())[i][2])

    def test_changed_source_and_nested_or_existing_output_refused(self):
        with fixture_dir() as t:
            project=project_fixture(t);key=project.rows[0]['id'];project.preview(key);project.approve(key)
            with self.assertRaisesRegex(ValueError,'source|input|nested'): project.generate(Path(t)/'Data/out')
            with self.assertRaisesRegex(ValueError,'exist'): project.generate(Path(t)/'Data')
            (Path(t)/'Data/meshes/weapons/bow.nif').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'changed'): project.generate(Path(t)/'Output')
            self.assertFalse((Path(t)/'Output').exists())

    def test_hand_change_invalidates_and_save_load_rechecks(self):
        from patcher_project import Project
        with fixture_dir() as t:
            project=project_fixture(t);key=project.rows[0]['id'];project.preview(key);project.approve(key)
            saved=project.document();loaded=Project.restore(saved)
            self.assertTrue(loaded.rows[0]['approved'])
            project.set_hand('right');self.assertFalse(project.rows[0]['approved'])
            with self.assertRaises(ValueError): project.set_hand('banana')
            saved['rows'][0]['sha256']='0'*64
            loaded=Project.restore(saved);self.assertFalse(loaded.rows[0]['approved'])

    def test_approval_requires_successful_current_preview(self):
        with fixture_dir() as t:
            project=project_fixture(t);key=project.rows[0]['id']
            with self.assertRaisesRegex(ValueError,'preview'): project.approve(key)
            project.preview(key);project.update(key,dict(shelf=6))
            with self.assertRaisesRegex(ValueError,'preview'): project.approve(key)


class ServerTests(unittest.TestCase):
    def test_request_waiting_for_lock_cannot_mutate_running_export(self):
        from patcher_server import make_server
        class ObservedLock:
            def __init__(self): self.lock=threading.RLock();self.waiting=threading.Event()
            def __enter__(self):
                if threading.current_thread().name!='MainThread':self.waiting.set()
                self.lock.acquire();return self
            def __exit__(self,*args):self.lock.release()
        with fixture_dir() as t:
            server=make_server(port=0);server.project=project_fixture(t);server.lock=ObservedLock()
            service=threading.Thread(target=server.serve_forever,daemon=True);service.start();responses=[]
            def request():
                c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
                c.request('POST','/api/hand',json.dumps({'hand':'right'}),{'X-Bow-Token':server.token})
                r=c.getresponse();r.read();responses.append(r.status);c.close()
            try:
                with server.lock:
                    caller=threading.Thread(target=request);caller.start()
                    self.assertTrue(server.lock.waiting.wait(3));server.job={'state':'running','message':'Exporting'}
                caller.join(5)
                self.assertEqual(responses,[400]);self.assertEqual(server.project.hand,'left')
            finally:server.shutdown();server.server_close();service.join()

    def test_loopback_api_requires_token_and_checks_origin(self):
        from patcher_server import make_server
        server=make_server(port=0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            connection=http.client.HTTPConnection('127.0.0.1',server.server_port)
            connection.request('GET','/api/status');response=connection.getresponse();response.read()
            self.assertEqual(response.status,403)
            connection.request('GET','/api/status',headers={'X-Bow-Token':server.token,'Origin':'https://untrusted.example'})
            response=connection.getresponse();response.read();self.assertEqual(response.status,403)
            connection.request('GET','/api/status',headers={'X-Bow-Token':server.token})
            response=connection.getresponse();data=json.loads(response.read());self.assertEqual(response.status,200)
            self.assertEqual(data['job']['state'],'idle')
            connection.request('GET','/api/status',headers={'X-Bow-Token':server.token,'Host':'attacker.example'})
            response=connection.getresponse();response.read();self.assertEqual(response.status,403)
            connection.close()
        finally: server.shutdown();server.server_close();thread.join()


if __name__=='__main__': unittest.main()
