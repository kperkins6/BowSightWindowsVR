"""Fail if tracked files contain private paths, credentials or excluded assets."""
from pathlib import Path
import re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def audit():
 top=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ROOT,text=True).strip()).resolve()
 if top!=ROOT:raise RuntimeError('Run in the dedicated project repository')
 names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0');names=[n for n in names if n]
 if not names:raise RuntimeError('No tracked files; stage the intended public sources first')
 blocked={'.nif','.bsa','.dds','.bilab','.log','.exe','.dll','.obj','.zip','.7z'};errors=[]
 for name in names:
  p=ROOT/name
  if p.suffix.lower() in blocked:errors.append(name+': excluded asset/binary/archive')
  if p.suffix.lower()=='.png':continue
  content=p.read_text(encoding='utf-8')
  needles=['C:'+'/'+'Users/','C:'+'\\'+'Users\\','One'+'Drive','SkyrimVR'+'_Overhaul']
  if any(n.casefold() in content.casefold() for n in needles):errors.append(name+': private installation path')
  if re.search(r'gh[pousr]_[A-Za-z0-9]{20,}',content):errors.append(name+': credential-like token')
 if errors:raise RuntimeError('\n'.join(errors))
 print(f'Public-source audit passed: {len(names)} tracked files; no game meshes, private paths or credential-like tokens.')
if __name__=='__main__':audit()
