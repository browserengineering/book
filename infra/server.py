#!/usr/bin/env python

from http import server

# Based on code from https://stackoverflow.com/questions/12499171/
class WBEServer(server.SimpleHTTPRequestHandler):
    def end_headers(self):
        if self.path.startswith("widgets/"):
            self.send_header("Cross-Origin-Opener-Policy", "same-origin");
            self.send_header("Cross-Origin-Embedder-Policy", "require-corp");
        self.send_header('Cache-Control', 'no-store, must-revalidate')
        self.send_header('Expires', '0')

        server.SimpleHTTPRequestHandler.end_headers(self)

if __name__ == '__main__':
    server.test(HandlerClass=WBEServer)
