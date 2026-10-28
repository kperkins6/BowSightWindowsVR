"""Launch the local Bow Sight Patcher. Requires only Python 3.11+."""
import argparse
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mo2',help='ModOrganizer.ini or its folder')
    parser.add_argument('--profile',help='MO2 profile name (defaults to selected profile)')
    parser.add_argument('--data',help='Deployed/virtualized game Data folder')
    parser.add_argument('--plugins',help='Active plugins.txt for deployed mode')
    parser.add_argument('--ini',help='Explicit game INI for custom resource archive loading')
    parser.add_argument('--port',type=int,default=0,help='Local port; default selects an available port')
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--pick',choices=('file','directory'),help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.pick:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
        result=filedialog.askdirectory(parent=root) if args.pick=='directory' else filedialog.askopenfilename(parent=root)
        root.destroy();print(result);return
    if sys.version_info<(3,11): parser.error('Python 3.11 or newer is required')
    sys.path.insert(0,str(Path(__file__).resolve().parent/'tools'))
    from patcher_server import make_server
    defaults={k:v for k,v in vars(args).items() if k in ('mo2','profile','data','plugins','ini') and v}
    defaults['mode']='mo2' if args.mo2 or not args.data else 'data'
    server=make_server(args.port,defaults)
    url='http://127.0.0.1:'+str(server.server_port)
    print('Bow Sight Patcher: '+url,flush=True)
    print('Keep this window open while editing. Ctrl+C stops the patcher.',flush=True)
    if not args.no_browser:
        import webbrowser
        webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__=='__main__': main()
