# ==============================================================================
#
#                              |    |    |
#                             )_)  )_)  )_)
#                            )___))___))___)\
#                           )____)____)_____)\\
#                         _____|____|____|____\\\__
#                    ~~~~~\                   /~~~~~
#                     ~~~~~~^~~~~~~~~^^^^~~~~~~~~~~
#
#   ____                 _                   ____              _
#  / ___|  ___  __ _  __| | ___   __ _ ___  | __ )  ___   ___ | |_ _   _
#  \___ \ / _ \/ _` |/ _` |/ _ \ / _` / __| |  _ \ / _ \ / _ \| __| | | |
#   ___) |  __/ (_| | (_| | (_) | (_| \__ \ | |_) | (_) | (_) | |_| |_| |
#  |____/ \___|\__,_|\__,_|\___/ \__, |___/ |____/ \___/ \___/ \__|\__, |
#                               |___/                             |___/
#
# ==============================================================================
#
#                        NOT ALL BOOTY COMES IN A CHEST.
#
#                           github.com/SeadogsBooty
#
# ==============================================================================

import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from test_bridge import b, CFG, A
import install


class ApiSecurityTests(unittest.TestCase):
    def test_authenticated_redirects_do_not_forward_credentials(self):
        received=[]
        class Receiver(BaseHTTPRequestHandler):
            def do_GET(self):
                received.append(dict(self.headers))
                self.send_response(200); self.end_headers(); self.wfile.write(b'{}')
            do_POST = do_GET
            def log_message(self, *args): pass
        second=ThreadingHTTPServer(('127.0.0.1',0),Receiver)
        class Redirect(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(int(self.path.split('/')[-1]))
                self.send_header('Location','http://127.0.0.1:'+str(second.server_port)+'/receive')
                self.end_headers()
            do_POST = do_GET
            def log_message(self,*args): pass
        first=ThreadingHTTPServer(('127.0.0.1',0),Redirect)
        threads=[]
        for server in (first, second):
            thread=threading.Thread(target=server.serve_forever, daemon=True)
            thread.start(); threads.append(thread)
        try:
            base='http://127.0.0.1:'+str(first.server_port)
            for key in ('Authorization','X-Api-Key'):
                for code in (301,302,303,307,308):
                    for method in ('GET','POST'):
                        with self.subTest(key=key,code=code,method=method):
                            with self.assertRaisesRegex(RuntimeError,'redirect blocked'):
                                b.request(base,{key:'dummy'},method,'/'+str(code),{} if method=='POST' else None)
            self.assertEqual(received,[])
            self.assertEqual(b.request(base,{},'GET','/302'),(200,{}))
            self.assertEqual(len(received),1)
        finally:
            for server in (first,second):
                server.shutdown(); server.server_close()
            for thread in threads: thread.join()

    def test_no_redirect_even_same_origin_or_https_downgrade(self):
        import urllib.request
        handler=b.NoAuthRedirect()
        req=urllib.request.Request('https://example.invalid/api',headers={'Authorization':'dummy'})
        for target in ('https://example.invalid/other','http://example.invalid/api','https://other.invalid/api'):
            self.assertIsNone(handler.redirect_request(req,None,302,'',{},target))

    def test_runtime_private_file_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            config=root/'config.env'
            config.write_text('LIDARR_API_KEY=dummy\n'); config.chmod(0o600)
            self.assertEqual(b.read_config(config),{'LIDARR_API_KEY':'dummy'})
            config.chmod(0o644)
            with self.assertRaisesRegex(RuntimeError,'Unsafe permissions'): b.read_config(config)
            config.chmod(0o600)
            link=root/'link'; link.symlink_to(config)
            with self.assertRaisesRegex(RuntimeError,'Cannot safely read'): b.read_config(link)
            hard=root/'hard'; os.link(config,hard)
            with self.assertRaisesRegex(RuntimeError,'Unsafe permissions'): b.read_config(config)
            hard.unlink()
            with patch.object(b,'BASE',root):
                (root/'activity.jsonl').symlink_to(config)
                b.record(CFG,A,'error','dummy')
                self.assertEqual(config.read_text(),'LIDARR_API_KEY=dummy\n')

    def test_in_place_installer_restricts_permissions_and_rejects_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'soulsync'; target.mkdir(mode=0o755)
            for name in install.FILES:
                (target/name).write_text('example')
                (target/name).chmod(0o644)
            (target/'README.md').unlink()
            (target/'README.md').symlink_to(target/'LICENSE')
            with self.assertRaisesRegex(RuntimeError,'Unsafe installation file'):
                install.save(target,target,CFG)
            self.assertFalse((target/'config.env').exists())
            (target/'README.md').unlink(); (target/'README.md').write_text('example')
            install.save(target,target,CFG)
            self.assertEqual(target.stat().st_mode & 0o777,0o700)
            for name in install.FILES:
                self.assertEqual((target/name).stat().st_mode & 0o777,0o700 if name.endswith('.py') else 0o600)

    def test_runtime_unsafe_lock_cannot_overwrite_other_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); secret=root/'other'
            secret.write_text('unchanged'); secret.chmod(0o600)
            (root/'bridge.lock').symlink_to(secret)
            with patch.object(b,'BASE',root), patch.object(b,'config',return_value=CFG), patch('sys.argv',['bridge','--bulk','--apply']), patch.object(b,'lidarr') as read:
                self.assertEqual(b.main(),1); read.assert_not_called()
            self.assertEqual(secret.read_text(),'unchanged')


if __name__=='__main__': unittest.main()
