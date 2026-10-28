"""Package only Git-tracked public source/documentation, never local mesh builds."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,zipfile
from audit_public import audit
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--version',default='1.1.0-preview');args=parser.parse_args()
 if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?',args.version):parser.error('Invalid package version')
 audit();files=[n for n in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if n]
 out=ROOT/'dist';out.mkdir(exist_ok=True);archive=out/f'BowSightWindowsVR-{args.version}-SourceToolkit.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for name in sorted(files):
   info=zipfile.ZipInfo('BowSightWindowsVR/'+name,(2026,10,26,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,(ROOT/name).read_bytes())
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None;assert not any(Path(n).suffix.lower() in ('.nif','.bsa','.dds') for n in z.namelist())
 digest=hashlib.sha256(archive.read_bytes()).hexdigest();(out/'SHA256SUMS.txt').write_text(digest+'  '+archive.name+'\n')
 print(json.dumps(dict(archive=str(archive),files=len(files),sha256=digest),indent=2))
