from http.server import HTTPServer, BaseHTTPRequestHandler
from os import curdir, sep, path


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        try:
            if(path.isdir(self.path)):
                self.send_response(403)
                self.wfile.write(str.encode("Listing of directories not permited on this server"))
            else:
                f = open(curdir + sep + self.path, 'rb')
                self.wfile.write(f.read())
                f.close()
        except IOError:
            print("File "+self.path+" not found")
            self.send_response(404)


if __name__ == '__main__':
    httpd = HTTPServer(('localhost', 9080), SimpleHTTPRequestHandler)
    httpd.serve_forever()
