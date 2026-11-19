"""Loopback-only API and static React host. No message-writing or sending routes."""
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from .analytics import Analytics
from .contacts import Contacts

ROOT=Path(__file__).resolve().parent.parent/'frontend'/'dist'
LOCK=threading.RLock()
CONTACTS=Contacts()
DATA=Analytics(CONTACTS)
ERROR=None
try:
    DATA.load()
except Exception:
    ERROR='Messages could not be read. Check Full Disk Access for the app running this server, then retry.'


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass  # No private identifiers or request URLs in logs.

    def send(self,status,body,content_type='application/json'):
        if isinstance(body,(dict,list)):
            body=json.dumps(body,ensure_ascii=False,allow_nan=False).encode()
        elif isinstance(body,str):
            body=body.encode()
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def trusted(self):
        host=self.headers.get('Host','')
        origin=self.headers.get('Origin')
        return host in ('127.0.0.1:8501','localhost:8501') and (not origin or origin in ('http://127.0.0.1:8501','http://localhost:8501','http://127.0.0.1:5173')) and self.headers.get('Sec-Fetch-Site')!='cross-site'

    def do_GET(self):
        if not self.trusted():
            return self.send(403,{'error':'Local access only.'})
        route=urlparse(self.path)
        q=parse_qs(route.query)
        try:
            if route.path=='/api/health':
                return self.send(200,{'ok':True,'messages_ready':ERROR is None,'read_only':True})
            if route.path.startswith('/api/'):
                with LOCK:
                    if route.path=='/api/status':
                        return self.send(200,{'contacts':CONTACTS.status(),'error':ERROR,'read_only':True})
                    if ERROR:
                        return self.send(503,{'error':ERROR})
                    year=q.get('year',['all'])[0]
                    self.validate_year(year)
                    if route.path=='/api/summary':
                        return self.send(200,DATA.summary(year))
                    if route.path.startswith('/api/people/'):
                        return self.send(200,DATA.person(route.path.rsplit('/',1)[-1],year))
                    if route.path=='/api/onthisday':
                        return self.send(200,DATA.on_this_day())
                    if route.path=='/api/network':
                        return self.send(200,DATA.network(year))
                    if route.path=='/api/search':
                        return self.send(200,DATA.search(q.get('q',[''])[0][:200],year,q.get('person',[None])[0]))
                    if route.path=='/api/compare':
                        left=q.get('before',[''])[0];right=q.get('after',[''])[0]
                        self.validate_year(left,False);self.validate_year(right,False)
                        return self.send(200,DATA.compare(left,right))
                    return self.send(404,{'error':'Unknown endpoint.'})
            path=(ROOT/unquote(route.path).lstrip('/')).resolve()
            if not path.is_relative_to(ROOT.resolve()):
                return self.send(403,{'error':'Invalid path.'})
            if not path.is_file():
                path=ROOT/'index.html'
            if not path.exists():
                return self.send(503,'Build the React frontend with npm run build.','text/plain')
            return self.send(200,path.read_bytes(),mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
        except ValueError:
            self.send(400,{'error':'Choose a valid calendar year.'})
        except KeyError:
            self.send(404,{'error':'Person not found. Refresh your contacts and try again.'})
        except (BrokenPipeError,ConnectionResetError):
            pass
        except Exception:
            self.send(500,{'error':'This analysis could not be completed. Try refreshing the local data.'})

    @staticmethod
    def validate_year(value,allow_all=True):
        if allow_all and value=='all':
            return
        if not value.isdigit() or not 2001<=int(value)<=2100:
            raise ValueError('Invalid year')

    def do_POST(self):
        global ERROR
        if not self.trusted() or self.headers.get('X-Wrapped-Client')!='local':
            return self.send(403,{'error':'Use the local dashboard to retry.'})
        with LOCK:
            if self.path=='/api/contacts/refresh':
                result=CONTACTS.refresh();DATA.reindex()
                return self.send(200,result)
            if self.path=='/api/contacts/authorize':
                result=CONTACTS.request_access();DATA.reindex()
                return self.send(200,result)
            if self.path=='/api/refresh':
                try:
                    DATA.load();ERROR=None
                    return self.send(200,{'ok':True})
                except Exception:
                    ERROR='Messages could not be read. Check Full Disk Access and retry.'
                    return self.send(503,{'error':ERROR})
            self.send(404,{'error':'Unknown endpoint.'})


if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',8501),Handler)
    print('iMessage Wrapped → http://127.0.0.1:8501 (Messages read-only)',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
