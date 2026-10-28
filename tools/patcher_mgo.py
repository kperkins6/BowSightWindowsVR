"""Bounded MGO discovery and the explicit scan/build/approve/export shortcut."""
from datetime import datetime
from pathlib import Path
import os
import re
import uuid

from patcher_project import Project
from patcher_scan import mo2_settings,scan


def validate_mgo(ini):
    mo=mo2_settings(ini);ini=Path(mo['mo2'])
    name=re.sub(r'[^a-z0-9]','',ini.parent.name.lower())
    text=ini.read_text(encoding='utf-8-sig').lower()
    if not (name.startswith('mgo') or 'madgod' in name or 'mad god' in text or 'launch mgo' in text):
        raise ValueError('This MO2 installation was not identified as MGO')
    profile=mo['profile']
    if Path(profile).name!=profile or profile in ('.','..'):raise ValueError('Invalid MGO profile name')
    folder=Path(mo['profiles'])/profile
    if not (folder/'modlist.txt').is_file() or not (folder/'plugins.txt').is_file():
        raise ValueError('MGO active profile is missing modlist.txt or plugins.txt')
    if not Path(mo['mods']).is_dir() or not Path(mo['data']).is_dir():
        raise ValueError('MGO mods or game Data folder is missing')
    return dict(ini=str(ini),name=ini.parent.name,profile=profile,data=mo['data'])


def discovery_roots():
    roots=[Path.home(),Path.home()/'Games',Path.home()/'Documents',Path.home()/'Downloads']
    if os.name=='nt':
        import ctypes
        get_type=ctypes.windll.kernel32.GetDriveTypeW;get_type.argtypes=[ctypes.c_wchar_p];get_type.restype=ctypes.c_uint
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            drive=letter+':\\'
            if get_type(drive)==3:roots.append(Path(drive))
    return roots


def detect_mgo(configured=None,roots=None):
    if configured:
        try:return [validate_mgo(configured)]
        except (OSError,ValueError):pass
    found={}
    for root in discovery_roots() if roots is None else roots:
        root=Path(root)
        for pattern in ('MGO*/ModOrganizer.ini','*Mad*God*/ModOrganizer.ini','*/MGO*/ModOrganizer.ini','*/*Mad*God*/ModOrganizer.ini'):
            try:
                for ini in root.glob(pattern):
                    if len(found)>=32:return list(found.values())
                    try:
                        target=validate_mgo(ini);found[target['ini']]=target
                    except (OSError,ValueError):pass
            except OSError:pass
    return sorted(found.values(),key=lambda item:item['ini'].lower())


def build_mgo(ini,hand,output_root,progress=None):
    if hand not in ('left','right'):raise ValueError('Choose left- or right-handed output')
    target=validate_mgo(ini)
    if progress:progress('Scanning '+target['name']+' · '+target['profile'])
    inventory=scan(dict(mode='mo2',mo2=target['ini'],profile=target['profile']),progress)
    project=Project(inventory,hand)
    report=project.prepare_defaults(progress)
    result=dict(action='mgo',installation=target,hand=hand,count=0,path=None,zip=None,report=report)
    if not report['successes']:return result,project
    if progress:progress('Approving '+str(len(report['successes']))+' validated meshes')
    project.approve_defaults(report['id'])
    name='MGO-Bow-Sight-Windows-'+hand+'-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    output=Path(output_root).resolve()/name
    if progress:progress('Generating the MGO mod folder and installer ZIP')
    result.update(project.generate(output))
    result['report']=project.default_status()
    return result,project
