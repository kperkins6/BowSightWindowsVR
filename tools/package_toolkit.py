"""Package only Git-tracked public source/documentation, never local mesh builds."""
from pathlib import Path
import hashlib,json,subprocess,zipfile
from audit_public import audit
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 audit();files=[n for n in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if n]
 out=ROOT/'dist';out.mkdir(exist_ok=True);archive=out/'BowSightWindowsVR-1.0.0-SourceToolkit.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for name in sorted(files):
   info=zipfile.ZipInfo('BowSightWindowsVR/'+name,(2026,10,26,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,(ROOT/name).read_bytes())
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None;assert not any(Path(n).suffix.lower() in ('.nif','.bsa','.dds') for n in z.namelist())
 digest=hashlib.sha256(archive.read_bytes()).hexdigest();(out/'SHA256SUMS.txt').write_text(digest+'  '+archive.name+'\n')
 print(json.dumps(dict(archive=str(archive),files=len(files),sha256=digest),indent=2))
