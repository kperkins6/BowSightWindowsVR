"""Mod-manager-independent bow inventory with an MO2 profile adapter."""
import configparser
import hashlib
from pathlib import Path
import re
from patcher_assets import AssetIndex, MARKER, asset_path, find_file
from patcher_records import discover_bows

STOCK=('skyrim.esm','update.esm','dawnguard.esm','hearthfires.esm','dragonborn.esm','skyrimvr.esm')


def lines(path):
    return [s.strip() for s in Path(path).read_text(encoding='utf-8-sig').splitlines()
            if s.strip() and not s.lstrip().startswith('#')]


def ini_value(value):
    value=value.strip()
    if value.startswith('@ByteArray(') and value.endswith(')'): value=value[11:-1]
    return value.replace('\\\\','\\').strip('"')


def mo2_settings(ini):
    ini=Path(ini).resolve()
    if ini.is_dir(): ini=ini/'ModOrganizer.ini'
    cp=configparser.ConfigParser(interpolation=None,strict=False)
    cp.read(ini,encoding='utf-8-sig')
    if not cp.has_section('General'): raise ValueError('Select a valid ModOrganizer.ini')
    general=dict(cp['General']); settings=dict(cp['Settings']) if cp.has_section('Settings') else {}
    values={**general,**settings}
    base=ini.parent
    def expand(value,default):
        value=ini_value(value or str(default)).replace('%BASE_DIR%',str(base)).replace('%base_dir%',str(base))
        p=Path(value)
        return (base/p).resolve() if not p.is_absolute() else p.resolve()
    base=expand(values.get('base_directory'),base)
    game=expand(general.get('gamepath'),base)
    return dict(mo2=str(ini),data=str(game/'Data'),gameName=general.get('gamename','Skyrim Special Edition'),
                mods=str(expand(values.get('mod_directory'),base/'mods')),
                profiles=str(expand(values.get('profiles_directory'),base/'profiles')),
                overwrite=str(expand(values.get('overwrite_directory'),base/'overwrite')),
                profile=ini_value(general.get('selected_profile','Default')))


def configuration(config):
    config=dict(config);warnings=[];selection_paths=[]
    mode=config.get('mode','mo2')
    if mode=='mo2':
        mo=mo2_settings(config['mo2'])
        profile_name=config.get('profile') or mo['profile']
        if Path(profile_name).name!=profile_name or profile_name in ('.','..'): raise ValueError('Invalid profile name')
        profile=Path(mo['profiles'])/profile_name
        if not profile.is_dir(): raise ValueError('MO2 profile not found: '+str(profile))
        data=Path(config.get('data') or mo['data']).resolve()
        roots=[data]
        for name in reversed([s[1:] for s in lines(profile/'modlist.txt') if s.startswith('+')]):
            if Path(name).name!=name or name in ('.','..'): raise ValueError('Unsafe modlist entry')
            mod=Path(mo['mods'])/name
            if (mod/MARKER).exists() or name in ('[NoDelete] Bow Sight Windows','[NoDelete] Long Bow Left-Hand Sight Window'):
                warnings.append('Excluded existing generated mod: '+name);continue
            if not mod.is_dir(): raise FileNotFoundError('Enabled mod missing: '+str(mod))
            roots.append(mod)
        overwrite=Path(mo['overwrite'])
        if overwrite.is_dir(): roots.append(overwrite)
        plugin_file=profile/'plugins.txt';order_file=profile/'loadorder.txt'
        config.update(mo,profile=profile_name,data=str(data),mode=mode)
        selection_paths.extend([Path(mo['mo2']),profile/'modlist.txt'])
        ini_candidates=[profile/n for n in ('skyrim.ini','skyrimvr.ini','Skyrim.ini','SkyrimVR.ini')]
        if not any(p.is_file() for p in ini_candidates):
            documents=Path.home()/'Documents'
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
                    import os
                    documents=Path(os.path.expandvars(winreg.QueryValueEx(key,'Personal')[0]))
            except (ImportError,OSError): pass
            game_name=mo['gameName'];ini_name='SkyrimVR.ini' if 'VR' in game_name.upper() else 'Skyrim.ini'
            ini_candidates.append(documents/'My Games'/game_name/ini_name)
    elif mode=='data':
        data=Path(config['data']).resolve();roots=[data]
        plugin_file=Path(config['plugins']).resolve()
        order_file=Path(config.get('loadorder') or plugin_file)
        ini_candidates=[Path(config['ini'])] if config.get('ini') else []
    else: raise ValueError('Choose MO2 or deployed Data mode')
    if not data.is_dir(): raise ValueError('Game Data folder not found')
    if mode=='data' and (data/MARKER).exists(): raise ValueError('Select original game Data, not generated output')
    active_lines=lines(plugin_file)
    starred=any(s.startswith('*') for s in active_lines)
    active={s.lstrip('*').lower() for s in active_lines if s.startswith('*') or not starred}
    available={}
    for root in roots:
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in ('.esm','.esp','.esl'): available[p.name.lower()]=p
    active.update(n for n in STOCK if n in available)
    order=[s.lstrip('*').lower() for s in lines(order_file) if s.lstrip('*').lower() in active] if order_file.exists() else []
    # Master files are force-loaded even when plugins.txt omits them.
    order=list(dict.fromkeys([n for n in STOCK if n in active]+order+[s.lstrip('*').lower() for s in active_lines if s.lstrip('*').lower() in active]))
    missing=active-set(available)
    if missing: raise FileNotFoundError('Enabled plugins missing: '+', '.join(sorted(missing)))
    if config.get('ini'): ini_candidates=[Path(config['ini'])]
    selection_paths.extend([plugin_file,order_file]+[p for p in ini_candidates if p.is_file()])
    config['_selectionSnapshots']={str(p.resolve()):[p.stat().st_size,p.stat().st_mtime_ns] for p in set(selection_paths) if p.is_file()}
    archives=[]
    ini_used=set()
    for ini in ini_candidates:
        if not ini.is_file() or ini.resolve() in ini_used: continue
        ini_used.add(ini.resolve())
        cp=configparser.ConfigParser(interpolation=None,strict=False);cp.read(ini,encoding='utf-8-sig')
        if cp.has_section('Archive'):
            for key,value in cp['Archive'].items():
                if key.lower().startswith('sresourcearchive'):
                    archives.extend(n.strip() for n in value.split(',') if n.strip())
    if not archives:
        warnings.append('No effective archive INI supplied: using standard Skyrim archives plus active-plugin BSAs. Supply the game INI if archive loading is customized.')
    return config,roots,[available[n] for n in order],archives,warnings


def scan(config, progress=None):
    config,roots,plugins,archives,warnings=configuration(config)
    assets=AssetIndex(roots,[p.name for p in plugins],archives,progress)
    warnings.extend(assets.warnings)
    records=discover_bows(plugins,progress,warnings)
    entries={}
    for bow in records:
        for model,role in ((bow.get('model'),'world'),(bow.get('firstPersonModel'),'first person')):
            if not model:
                if role=='world': warnings.append('Bow has no resolved model: '+bow['id'])
                continue
            try:
                rel=asset_path(model)
                if rel.startswith('meshes/'): rel=rel[7:]
                if not rel.endswith('.nif'): raise ValueError('Model is not a NIF')
            except ValueError as e:
                warnings.append(bow['id']+': '+str(e));continue
            names=[(rel,role)]
            stem=Path(rel).stem
            for name,label in (('1stperson'+stem,'first-person variant'),(stem+'disp','display variant')):
                variant=Path(rel).with_name(name+'.nif').as_posix()
                if assets.exists('meshes/'+variant): names.append((variant,label))
            for path,label in names:
                row=entries.setdefault(path,dict(id=hashlib.sha256(path.encode()).hexdigest()[:16],path=path,weapons=[],roles=[]))
                reference={k:bow[k] for k in ('id','editor','provider')}
                if reference not in row['weapons']: row['weapons'].append(reference)
                if label not in row['roles']: row['roles'].append(label)
    rows=[]
    for i,row in enumerate(sorted(entries.values(),key=lambda r:r['path'])):
        if progress: progress(f'Checking mesh {i+1}/{len(entries)}: '+row['path'])
        try:
            data,source=assets.read('meshes/'+row['path'])
            row.update(source=source,sha256=hashlib.sha256(data).hexdigest(),size=len(data))
        except (OSError,ValueError,KeyError) as e: row['error']=str(e)
        rows.append(row)
    return dict(config=config,bows=rows,warnings=warnings,weaponCount=len(records),
                pluginCount=len(plugins),roots=[str(p) for p in roots],archives=archives,
                plugins=[p.name for p in plugins],
                pluginSnapshots={str(p.resolve()):[p.stat().st_size,p.stat().st_mtime_ns] for p in plugins})


def assets_for(inventory):
    return AssetIndex(inventory['roots'],inventory['plugins'],inventory.get('archives',()))
