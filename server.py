import socket
import socket
import os
import stat
import sys
import urllib.parse
import datetime
from threading import Thread
from argparse import ArgumentParser

BUFSIZE = 4096
CRLF = '\r\n'
OK = 'HTTP/1.1 200 OK{}{}{}'.format(CRLF, CRLF, CRLF)
OK_ONECRLF = 'HTTP/1.1 200 OK{}'.format(CRLF)
NOT_FOUND = 'HTTP/1.1 404 NOT FOUND{}Connection: close{}{}'.format(CRLF, CRLF, CRLF)
FORBIDDEN = 'HTTP/1.1 403 FORBIDDEN{}Connection: close{}{}'.format(CRLF, CRLF, CRLF)
METHOD_NOT_ALLOWED = 'HTTP/1.1 405 METHOD NOT ALLOWED{}Allow: GET, HEAD, POST {}Connection: close{}{}'.format(CRLF, CRLF, CRLF, CRLF)
NOT_ACCEPTABLE = 'HTTP/1.1 406 NOT ACCEPTABLE{}Connection: close{}{}'.format(CRLF, CRLF, CRLF)
MOVED_PERMANENTLY = 'HTTP/1.1 301 MOVED PERMANENTLY{}Location: https://www.youtube.com{}Connection: close{}{}'.format(CRLF, CRLF, CRLF, CRLF)

def get_contents(fname):
     f = open(fname, 'r')
     return f.read()

def check_perms(resource):
     """Returns True if resource has read permissions set on
    'others'"""
     stmode = os.stat(resource).st_mode
     return (getattr(stat, 'S_IROTH') & stmode) > 0

def client_talk(client_sock, client_addr):
     print('talking to {}'.format(client_addr))
     data = client_sock.recv(BUFSIZE)
     while data:
         print(data.decode('utf-8'))
         data = client_sock.recv(BUFSIZE)
     # clean up
     client_sock.shutdown(1)
     client_sock.close()
     print('connection closed.')

class HTTP_Server:
    def __init__(self, host, port):
        print('listening on port {}'.format(port))
        self.host = host
        self.port = port
        self.setup_socket()
        self.accept()
        self.sock.shutdown()
        self.sock.close()

    def setup_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(128)

    def accept(self):
        while True:
            (client, address) = self.sock.accept()
            th = Thread(target=self.accept_request, args=(client, address))
            th.start()

     # here, we add a function belonging to the class to accept
     # and process a request
    def accept_request(self, client_sock, client_addr):
        print("accept request")
        data = client_sock.recv(BUFSIZE)
        req = data.decode('utf-8') #returns a string
        response=self.process_request(req) #returns a string
        #once we get a response, we chop it into utf encoded bytes
        #and send it (like EchoClient)
        client_sock.send(response)
        #clean up the connection to the client
        #but leave the server socket for recieving requests open
        client_sock.shutdown(1)
        client_sock.close()

    def process_request(self, request):
        print('######\nREQUEST:\n{}######'.format(request))

        '''splits the request into the header and the body'''
        headerAndBody = request.strip().split(CRLF+CRLF)

        '''splits the request line by line'''
        linelist = request.strip().split(CRLF)

        reqline = linelist[0]

        '''finds the line containing the accept requirements'''
        acceptline = ""
        for line in linelist:
            if "Accept:" in line:
                acceptline = line

        rlwords = reqline.split()

        if len(rlwords) == 0:
            return bytes('', 'utf-8')
        if rlwords[0] == 'HEAD':
            resource = rlwords[1][1:] # skip beginning /
            return self.head_request(resource, acceptline)
        elif rlwords[0] == 'GET':
            resource = rlwords[1][1:] # skip beginning /
            return self.get_request(resource, acceptline)
        elif rlwords[0] == 'POST':
            return self.post_request(headerAndBody[1])
        else:
            return bytes(METHOD_NOT_ALLOWED,'utf-8')

    def head_request(self, resource, acceptline):
        path = os.path.join('.', resource) #look in directory where server is running
        if not os.path.exists(resource):
            ret = bytes(NOT_FOUND, 'utf-8')
        elif not check_perms(resource):
            ret = bytes(FORBIDDEN, 'utf-8')
        else:
            if path.endswith('.html'):
                '''checks if the html file can be accepted by the request'''
                if("text/html" not in acceptline and "*/*" not in acceptline):
                    ret = bytes(NOT_ACCEPTABLE,'utf-8')
                else:
                    ret = bytes(OK,'utf-8')
            elif path.endswith('.mp3'):
                '''checks if the mp3 file can be accepted by the request'''
                if("audio/*" not in acceptline and "*/*" not in acceptline):
                    ret = bytes(NOT_ACCEPTABLE,'utf-8')
                else:
                    ret = bytes(OK,'utf-8')
            elif path.endswith('.png'):
                '''checks if the png file can be accepted by the request'''
                if("image/*" not in acceptline and "*/*" not in acceptline):
                    ret = bytes(NOT_ACCEPTABLE,'utf-8')
                else:
                    ret = bytes(OK,'utf-8')
        return ret


    '''first if case handles case where the form sent a query string through the URI'''
    '''uses the unquote function to decode the ascii in the URI'''
    '''then splits the string at each & to get each name:value pair'''
    '''and iterate over them to add them to an HTML response'''
    def get_request(self, resource, acceptline):
        if resource[0:1] == '?':
            rawFormResponses = resource[1:]
            decodedFormResponses = urllib.parse.unquote(rawFormResponses)
            formResponses = decodedFormResponses.split('&')
            page_return = '<html><head><title>Form Responses</title></head><body><h1>Following Form Data Submitted Successfully:</h1><h2>'
            for response in formResponses:
                page_return += response + '</h2><h2>'
            page_return += '</h2></body></html>'
            ret = bytes(OK + page_return,'utf-8')
        elif resource[0:6] == 'mytube':
            ret = bytes(MOVED_PERMANENTLY,'utf-8')
        elif not os.path.exists(resource):
            file = open('./404.html')
            page_return = file.read()
            ret = bytes(NOT_FOUND + page_return, 'utf-8')
        elif not check_perms(resource):
            file = open('./403.html')
            page_return = file.read()
            ret = bytes(FORBIDDEN + page_return, 'utf-8')
        else:
            filePath = os.path.join('.', resource)
            if filePath.endswith('.html'):
                '''checks if the html file can be accepted by the request'''
                if("text/html" not in acceptline and "*/*" not in acceptline):
                    ret = bytes(NOT_ACCEPTABLE,'utf-8')
                else:
                    file = open(resource, 'r')
                    contents = file.read()
                    ret = bytes(OK + contents,'utf-8')
            elif filePath.endswith('.mp3'):
                '''checks if the mp3 file can be accepted by the request'''
                if("audio/*" not in acceptline and "*/*" not in acceptline):
                    ret = bytes(NOT_ACCEPTABLE,'utf-8')
                else:
                    file = open(resource, 'rb')
                    contents = file.read()
                    header = bytes(OK_ONECRLF,'utf-8')
                    contentType = bytes('Content-Type: audio/mpeg' + CRLF + CRLF, 'utf-8')
                    header = bytes(OK,'utf-8')
                    ret = header + contentType + contents
            elif filePath.endswith('.png'):
                '''checks if the png file can be accepted by the request'''
                if("image/*" not in acceptline and "*/*" not in acceptline):
                    ret = bytes(NOT_ACCEPTABLE,'utf-8')
                else:
                    file = open(resource, 'rb')
                    contents = file.read()
                    header = bytes(OK_ONECRLF,'utf-8')
                    contentType = bytes('Content-Type: image/png' + CRLF + CRLF, 'utf-8')
                    ret = header + contentType + contents
        return ret


    '''handles case where the form sent a with using POST'''
    '''uses the unquote function to decode the ascii in the URI'''
    '''then splits the string at each & to get each name:value pair'''
    '''and iterate over them to add them to an HTML response'''

    '''takes in only the body of the HTTP request'''
    def post_request(self, body):
        decodedBody = urllib.parse.unquote(body)
        formResponses = decodedBody.split('&')
        page_return = '<html><head><title>Form Responses</title></head><body><h1>Following Form Data Submitted Successfully:</h1><h2>'
        for response in formResponses:
            page_return += response + '</h2><h2>'
        page_return += '</h2></body></html>'
        return bytes(OK + page_return,'utf-8')

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--host', type=str, default='localhost',
    help='specify a host to operate on (default: localhost)')
    parser.add_argument('-p', '--port', type=int, default=9001, help='specify a port to operate on (default: 9001)')
    args = parser.parse_args()
    return (args.host, args.port)

if __name__ == '__main__':
    (host, port) = parse_args()
    HTTP_Server(host, port)
