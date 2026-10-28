"""Loopback-only API for the local bow sight workbench."""
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import subprocess
import sys
import threading
from urllib.parse import urlsplit

from patcher_project import Project, DEFAULTS
from patcher_scan import scan, mo2_settings

ROOT=Path(__file__).resolve().parents[1]


class LocalServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,port,defaults):
        super().__init__(('127.0.0.1',port),Handler)
        self.token=secrets.token_urlsafe(32);self.defaults=defaults or {}
        self.project=None;self.lock=threading.RLock();self.job=dict(state='idle',message='Choose your mod list to begin')

    def task(self,fn):
        with self.lock:
            if self.job['state']=='running': raise ValueError('Another operation is running')
            self.job=dict(state='running',message='Starting…')
        def run():
            try:
                result=fn(lambda message:self.job.update(message=message))
                with self.lock: self.job=dict(state='done',message='Ready',result=result)
            except Exception as e:
                with self.lock: self.job=dict(state='error',message=str(e) or type(e).__name__)
        threading.Thread(target=run,daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass

    def send(self,value,status=200,kind='application/json'):
        data=json.dumps(value,allow_nan=False).encode() if kind=='application/json' else value
        self.send_response(status);self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'")
        self.end_headers();self.wfile.write(data)

    def allowed(self,api=True):
        origin='http://127.0.0.1:'+str(self.server.server_port)
        host=self.headers.get('Host','')
        if host!='127.0.0.1:'+str(self.server.server_port): return False
        if self.headers.get('Origin',origin)!=origin: return False
        return not api or secrets.compare_digest(self.headers.get('X-Bow-Token',''),self.server.token)

    def do_GET(self):
        route=urlsplit(self.path).path
        if not self.allowed(route.startswith('/api/')): self.send(dict(error='Local request authorization failed'),403);return
        if route=='/api/status':
            with self.server.lock:
                self.send(dict(job=self.server.job,project=self.server.project.summary() if self.server.project and self.server.job['state']!='running' else None,
                               defaults=self.server.defaults,settings=DEFAULTS))
        elif route in ('/','/app.js','/viewer.js','/style.css','/mobile.css','/batch.css','/quick.css'):
            p=ROOT/'app'/('index.html' if route=='/' else route[1:])
            if not p.is_file(): self.send(dict(error='Application asset missing'),404);return
            data=p.read_bytes()
            if route=='/': data=data.replace(b'__SESSION_TOKEN__',self.server.token.encode())
            self.send(data,kind=mimetypes.guess_type(str(p))[0] or 'application/octet-stream')
        else: self.send(dict(error='Not found'),404)

    def do_POST(self):
        if not self.allowed(): self.send(dict(error='Local request authorization failed'),403);return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<8*1024*1024: raise ValueError('Invalid request size')
            value=json.loads(self.rfile.read(size));route=urlsplit(self.path).path
            if not isinstance(value,dict): raise ValueError('Expected JSON object')
            if route=='/api/scan':
                def work(progress):
                    inventory=scan(value,progress);progress('Checking bow geometry…')
                    project=Project(inventory)
                    with self.server.lock: self.server.project=project
                    return dict(action='scan')
                self.server.task(work);self.send(dict(started=True));return
            if route=='/api/load':
                def work(progress):
                    project=Project.restore(value,progress)
                    with self.server.lock: self.server.project=project
                    return dict(action='load')
                self.server.task(work);self.send(dict(started=True));return
            if route=='/api/mo2':
                config=mo2_settings(value['path'])
                config['profilesAvailable']=[p.name for p in Path(config['profiles']).iterdir() if p.is_dir() and (p/'modlist.txt').exists()]
                self.send(config);return
            if route=='/api/pick':
                kind=value.get('kind')
                if kind not in ('file','directory'): raise ValueError('Invalid dialog type')
                # Tk owns the main thread of a separate, short-lived process.
                result=subprocess.run([sys.executable,str(ROOT/'patcher.py'),'--pick',kind],capture_output=True,text=True,timeout=300)
                if result.returncode: raise ValueError('Native picker unavailable; enter the path directly')
                self.send(dict(path=result.stdout.strip()));return
            with self.server.lock:
                if self.server.job['state']=='running': raise ValueError('Wait for the current operation to finish')
                project=self.server.project
                if project is None: raise ValueError('Scan or load a project first')
                if route=='/api/preview': result=project.preview(value['id'])
                elif route=='/api/settings': result=project.update(value['id'],value.get('settings'),value.get('include'))
                elif route=='/api/hand': project.set_hand(value['hand']);result=project.summary()
                elif route=='/api/approve': project.approve(value['id']);result=project.row(value['id'])
                elif route=='/api/save': result=project.document()
                elif route=='/api/defaults-prepare':
                    def work(progress):
                        report=project.prepare_defaults(progress)
                        return dict(action='defaults',report=report)
                    self.server.task(work);result=dict(started=True)
                elif route=='/api/defaults-approve':
                    project.approve_defaults(value['id']);result=project.summary()
                elif route=='/api/batch':
                    report=project.batch(value['ids'],value['action'],value.get('settings'))
                    result=dict(project=project.summary(),report=report)
                elif route=='/api/skip-unreviewed':
                    for row in project.rows:
                        if not row['approved']: project.update(row['id'],include=False)
                    result=project.summary()
                elif route=='/api/generate':
                    def work(progress):
                        progress('Validating reviewed meshes and generating output…')
                        return dict(action='generate',**project.generate(value['output'],value.get('zip',True)))
                    self.server.task(work);result=dict(started=True)
                else: self.send(dict(error='Not found'),404);return
            self.send(result)
        except (ValueError,KeyError,StopIteration,OSError,AssertionError,TypeError) as e:
            self.send(dict(error=str(e) or type(e).__name__),400)
        except Exception as e:
            self.send(dict(error='Operation failed: '+(str(e) or type(e).__name__)),500)


def make_server(port=0,defaults=None):
    return LocalServer(port,defaults)
