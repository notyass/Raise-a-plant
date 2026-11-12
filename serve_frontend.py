"""Sert le frontend en développement : python serve_frontend.py

Équivaut à `python -m http.server 8080 --directory frontend`, mais interdit
au navigateur de garder les fichiers en mémoire. Sans cela, après une mise à
jour du code, le navigateur peut continuer d'afficher l'ancienne version des
fichiers JavaScript.
"""
import functools
import http.server
import os

PORT = 8080
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend')


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


if __name__ == '__main__':
    handler = functools.partial(NoCacheHandler, directory=FRONTEND_DIR)
    with http.server.ThreadingHTTPServer(('localhost', PORT), handler) as server:
        print(f"Frontend sur http://localhost:{PORT} (Ctrl+C pour arrêter)")
        server.serve_forever()
