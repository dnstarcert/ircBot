#!/usr/bin/env python
#-*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
#bugzilla http://bugzilla.gendalf.info/buglist.cgi?product=irc%20bot&component=all&resolution=---&list_id=2
#


import socket
import threading
import sys, inspect, os, tempfile,re
import os.path
import base64,urllib2
from urllib2 import Request, urlopen, URLError
from chardet.universaldetector import UniversalDetector
from urlparse import urlparse
import ConfigParser
import time
from daemon import Daemon
from PIL import Image
import string, StringIO

#sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
os.chdir(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
threadLife = True
path = os.path.abspath(os.path.dirname(__file__))
CHANNEL_RE = re.compile('PRIVMSG (#?[\w\-]+) :')
NICK_RE = re.compile(":([\w\-\[\]\|]+)!")
IMAGE_RE = re.compile(r"((ht|f)tps?:\/\/[\w\.-]+\/[\w\.-\/]+\.(jpg|png|gif|bmp))")
HTTP_RE  = re.compile(r"(https?:\/\/[^\s]+)")
class MyDaemon(Daemon): 
    def run(self):
        #print "daemon started"
        threadLife = True
        config = ConfigParser.RawConfigParser()
        config.read('%s/bot.cfg' % path)
        channels = config.get("bot", "channels").split(",")
        self.connectToServer(config.get("bot", "nick"),
                    config.get("bot", "server"),
                    config.get("bot", "port"))
    def connectToServer(self,NICK,HOST,PORT):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        my_nick = "NICK %s\n\r" % NICK
        sock.connect((HOST, int(PORT)))
        sock.send('PONG LAG123124124 \n\r')
        sock.send('USER Ghost 95 * :Phantom \n\r')
        sock.send(my_nick)
        #recv_data(sock)
        config = ConfigParser.RawConfigParser()
        config.read('%s/bot.cfg' % path)
        defaultEncoding = config.get("bot", "encoding")
        channels = config.get("bot", "channels").split(",")
        onStart = True
        t = threading.Thread(target=self.recv_data, args=(sock,onStart,my_nick,defaultEncoding,channels,))
        t.daemon = False
        t.setName("Read data")
        t.start()
        
    
    
    def recv_data(self,sock,onStart,my_nick,defaultEncoding,channels):
        global threadLife
        
        while threadLife : 
            try: 
                recv_data = sock.recv(4096)
            except:
                threadLife = False
                print "error"
                sock.close()
                #self.run()
                break
            if not recv_data:
                threadLife = False
                sock.close()
                print "error"
                #self.run()
                break
            else :
                #print recv_data
                #sys.stdout.write(recv_data)
                t = threading.Thread(target=self.worker, args=(recv_data,onStart,sock,my_nick,defaultEncoding,channels,))
                t.daemon = True
                t.setName("Data process")
                t.start()
    
    def worker(self,text,onStart,sock,my_nick,defaultEncoding,channels):
            #print text[:-2]
            if text.find("PING :") == 0:
                sock.send(u"%s\n\r" % (text.replace("PING", "PONG")))
            elif text.find("Global Users:") > 0 :
                onStart = False
                #print "JOIN: "
                charset = self.detect_encoding(text)
                for channel in channels :
                    sock.send('JOIN %s \n\r' % channel)
                #print "Connected"
                t = threading.Thread(target=self.send_ping, args=(sock,))
                t.daemon = True
                t.setName("ping")
                t.start()
    
            elif "JOIN :" in text: pass
                #sock.send("PRIVMSG %s :VERSION\n\r" % get_nick(recv_data))
            elif ":VERSION " in text:
                indx = text.rfind("VERSION")
                #print indx
                #print recv_data[indx:-3]
            elif " KICK #" in text:
                print "KICK"
                p = re.compile(r"( [a-zA-Z0-9].*) :")
                text2 = p.findall(text)[0]
                indx = text2.rfind("#")
                indx2 = text2[indx:].rfind(" ")
                indx3 = text.rfind(":")
                reason = text[indx3+1:]
                channel = text2[indx:indx + indx2]
                us_nick = text2[indx+indx2 + 1:]
                if us_nick == my_nick[5:-2]:
                   sock.send('JOIN %s \n\r' % channel)
            elif "VERSION" in text:
                #chat_box.append(repr(recv_data.decode("cp1251")))
                sock.send("NOTICE %s :VERSION Simple bot writen on python\n\r" % self.get_nick(text))
            elif "NICK" in text: pass
                #if get_nick(text) == my_nick:
                #    indx = text.rfind("NICK") + 6
                #    nick.setText(text[indx:])
                #    chat_box["RAW"].append("<font color=red>[%s] </font>\
                #        <font color=orange>Your nick is %s now</font>" \
                #        % (time.strftime("%H:%M:%S") ,text[indx:]))
    
            elif "PONG" in text: pass
    
            elif "PRIVMSG" in text: 
                t = threading.Thread(target=self.privmsg, args=(text,sock,))
                t.daemon = True
                t.setName("privmsg")
                t.start()
            
            else: 
                print ("Received data: ",
                    text[:-2].decode(defaultEncoding).encode("utf-8"))
    
    def privmsg(self,text,sock):
        channel = self.get_channel(text)
        nick = self.get_nick(text)
        indx = text.rfind("PRIVMSG") + len(channel) + 8
        color = re.compile(r'([0-9]{1,2})')
        text = color.sub("",text)
        text = text.replace("","")
        #print "%s" % text[indx:]
        #HTTP_RE  = re.compile(r"(http:\/\/[^\s]+)")
        #print HTTP_RE.search(text)
        try:
            if HTTP_RE.search(text):
                #print "#%s %s:%s" % (channel,nick,text)
                t = threading.Thread(target=self.http_title,args=(text, channel,sock,))
                t.daemon = True
                t.setName("http")
                t.start()
            if IMAGE_RE.search(text): 
                t = threading.Thread(target=self.link,
                    args=(text,))
                t.daemon = False
                t.setName("image")
                t.start()
        except: pass
    
    def http_title(self,text, channel,sock):
            headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:23.0) Gecko/20100101 Firefox/23.0'}
            m = HTTP_RE.findall(text)
            #print "m=%s" % m
            for x in xrange(len(m)):
                try:
                    url = m[x]
                    #print "url: %s" % url
                    request = urllib2.Request(url, None, headers)
                    res = urllib2.urlopen(request)
                    #print res.headers
                    info = res.info()
                    #print info
                    mimetype = info.getmaintype()
                    ext = info.getsubtype()
                    if mimetype != "image" and mimetype == "text" :
                        sech = re.compile(r"<title>(.*)<\/title>").findall(res.read())
                        charset = self.detect_encoding(sech[0])
                        text = sech[0].decode(charset).replace("\n","").replace("\r","")
                        color = re.compile(r'([0-9]{1,2})')
                        text = color.sub("",text)
                        if len(text) > 300 : text = text[:300]
                        if channel == "#trollsquad" or channel == "#test" : sock.send("PRIVMSG %s :05%s\n\r" \
                                                                            % (channel, text.encode("cp1251")))
                        res.close()
                    elif mimetype == "image":
                        img = Image.open(StringIO.StringIO(res.read()))
                        imagePath = "%s/images/%s" % (path,url.replace("/","_")) 
                        img.save("%s.%s" % (imagePath,ext))
                        res.close()


                except URLError, e: 
                    if hasattr(e, 'reason'): pass
                        #print 'We failed to reach a server.'
                        #print 'Reason: ', e.reason
                    elif hasattr(e, 'code'): pass
                        #print 'The server couldn\'t fulfill the request.'
                        #print 'Error code: ', e.code
    
    
    
    def link(self, text):
        m = IMAGE_RE.findall(text)
        for x in xrange(len(m)):
            url = m[x][0]
            print "url: %s" % url
            res = urllib2.urlopen(url)
            info = res.info()
            mimetype = info.getmaintype()
            if mimetype == "image":
                img = Image.open(StringIO.StringIO(res.read()))
                imagePath = "%s/images/%s" % (path,url.replace("/","_")) 
                img.save(imagePath) 
                res.close()

    def send_ping(self,sock):
            global threadLife
            while threadLife:
                time.sleep(10)
                sock.send("PING :LAG%s\n\r" % time.time())
    
    def detect_encoding(self,line):
            try:
                u = UniversalDetector()
                u.feed(line)
                u.close()
                result = u.result
                if result['encoding']:
                    if result['encoding'] == "ISO-8859-2": charset = "cp1251"
                    elif result['encoding'] == "ascii": charset = "utf-8"
                    elif result['encoding'] == "utf8": charset = "utf-8"
                    elif result['encoding'] == "windows-1251": charset = "cp1251"
                    elif result['encoding'].find("ISO-88") == 0: charset = "cp1251"
                    elif result['encoding'].find("windows") == 0: charset = "cp1251"
                    elif result['encoding'] == "MacCyrillic": charset = "cp1251"
                    else: charset = result['encoding']
                return charset
            except: return "utf-8"
    
    def get_channel(self,line):
            # line: irc.shock-world.com 319
        return CHANNEL_RE.search(line).group(1)
    
    def get_nick(self,line):
        return NICK_RE.match(line).group(1)   


if __name__ == "__main__":
	daemon = MyDaemon('/tmp/elis.pid')
	if len(sys.argv) == 2:
		if 'start' == sys.argv[1]:
			daemon.start()
		elif 'stop' == sys.argv[1]:
			daemon.stop()
		elif 'restart' == sys.argv[1]:
			daemon.restart()
		else:
			print "Unknown command"
			sys.exit(2)
		sys.exit(0)
	else:
		print "usage: %s start|stop|restart" % sys.argv[0]
		sys.exit(2)