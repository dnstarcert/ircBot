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
#db pass: O*%.:^8oF#]u=%z

import socket
import threading
import sys, inspect, os, tempfile,re,traceback
import os.path
import base64,urllib2,urllib
from urllib2 import Request, urlopen, URLError
from chardet.universaldetector import UniversalDetector
from urlparse import urlparse
import ConfigParser
import time
from daemon import Daemon
from PIL import Image
import string, StringIO
import MySQLdb
from hashlib import md5,sha512
import sqlite3
from cookielib import MozillaCookieJar
from cookielib import FileCookieJar
import multiprocessing as mp
from multiprocessing.managers import BaseManager
from Queue import Empty
from subprocess import Popen, PIPE
from signal import SIGTERM 
from HTMLParser import HTMLParser

#sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
os.chdir(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
threadLife = True
path = os.path.abspath(os.path.dirname(__file__))
CHANNEL_RE = re.compile('PRIVMSG (#?[\w\-]+) :')
NICK_RE = re.compile(":([\w\-\[\]\|`]+)!")
IMAGE_RE = re.compile(r"((ht|f)tps?:\/\/[\w\.-]+\/[\w\.-\/^,]+\.(jpg|png|gif|bmp))")
HTTP_RE  = re.compile(r"(https?:\/\/[^\s^,]+)")
IGNORE_RE = re.compile(r"(https?:\/\/pictures.gendalf.info)")
VIDEO_RE = re.compile(r"\'VIDEO_ID\': \"(?P<videoid>[\w\-\.]+?)\"")
YOUTUBE_RE = re.compile(r"(https?:\/\/www.youtube.com)")
SITE_RE = re.compile(r"(?P<site>https?:\/\/[a-zA-Z0-9\.]+)")
VK_RE = re.compile(r"(https?:\/\/vk.com)")
CHARSET_RE = re.compile('text/html; charset=([\w\s\-].*)\">')
AUDIO_RE = re.compile('<a class="current_audio fl_l" .*><div class="label fl_l"><\/div>(.*)<\/a>')
VKMESSAGE_RE = re.compile('<tr id="mess([0-9]+?)"[\d\s\S\D]+?<a href=".*" class="mem_link" target="_blank">(.+?)<.*<div class="im_msg_text">(.*?)?<\/div>(.*<img src="(.+?)")?',re.UNICODE)
PID_RE= re.compile(r"freeman\s+([\d]+)?\s+")


basePath = "%s/%s" % (path,'logs.db')
dbl = sqlite3.connect(basePath)
base = dbl.cursor()
base.execute('CREATE TABLE IF NOT EXISTS logs (id int(3) PRIMARY KEY NOT NULL UNIQUE,nick text,datetime timestamp,txt text)')
dbl.commit()

vkcookie = MozillaCookieJar()
vkcookie.load("%s/vk.txt" % path)
vkopener = urllib2.build_opener(urllib2.HTTPCookieProcessor(vkcookie))

class QueueManager(BaseManager): pass
queue = mp.Queue()
#processes = dict()
class MyDaemon(Daemon): 
#class MyDaemon():    
        
    vk_user = ""
    vk_passwd = ""
    
    def proces(self,doing,name,pid):
        #global processes
        self.loger("action: %s => name : %s => pid: %s" % (doing,name,pid))
        if doing == "add":
            self.processes[name] = pid
        elif doing == "kill":
            self.processes[name].terminate()
        elif doing == "del":
            del self.processes[name]
        sys.stderr.write(" %s \n" % self.processes )
        sys.stderr.flush()
    
    def terminate(self):
        #global processes  str=`ps auxw | grep elis.py | awk ' {print $2 } '`
        # kill -9 $str
        pr = mp.current_process()
        print "my pid = %s" % pr.pid
        p = Popen(['ps','auxw'], stdout=PIPE, stderr=PIPE)
        out,err = p.communicate()
        out = out.split('\n')
        for istr in out:
            if "elis.py" in istr:
                pid = int(PID_RE.match(istr).group(1))
                print pid
                #pid = int(istr.split(' ')[5])
                if int(pid) != int(pr.pid) :
                    #print "pid = %s , kill = %s" % (pr.pid,pid)
                    os.kill(pid, SIGTERM)
                    time.sleep(0.1)
                    #print out,err
        for i in self.dataProc:
            i.terminate()
        for item  in self.processes.values():
            item.terminate()
    
    def exterminate(self):
    	pr = mp.current_process()
    	pf = file('/tmp/elis.pid','r')
        pid = int(pf.read().strip())
        pf.close()
        
    	for name,pid1 in self.processes.items():
    	    sys.stderr.write("killing process: %s ==> pid=%s\n" % (name,pid1) )
            sys.stderr.flush()
            if int(pid1) != pid:
    	        os.kill(int(pid1), SIGTERM)
                time.sleep(0.1)
            else: 
                os.remove('/tmp/elis.pid')
                os.kill(pid, SIGTERM)

    def listProcesses(self):
        print self.processes
        sys.stdout.flush()
    #def start(self):
    #    self.run()

    def run(self):
        #print "daemon started"
        threadLife = True
        
        config = ConfigParser.RawConfigParser()
        config.read('%s/bot.cfg' % path)
        channels = config.get("bot", "channels").split(",")
        self.connectToServer(config.get("bot", "nick"),
                    config.get("bot", "server"),
                    config.get("bot", "port"))
        p = mp.current_process()
        self.proces("add", p.name, p.pid)
        self.loger(p)
        t = threading.Thread(target=self.processes1, args=())
        t.daemon = True
        t.setName("watch_dog")
        t.start()
        time.sleep(0.3)
        #QueueManager.register('get_queue', callable=lambda:queue)
        #m = QueueManager(address=('127.0.0.1', 50000), authkey='abracadabra')
        #s = m.get_server()
        #s.serve_forever()

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
        db_user=config.get("db", "user")
        db_passwd=config.get("db", "passwd")
        self.vk_user=config.get("vk", "email")
        self.vk_passwd=config.get("vk", "passwd")
        channels = config.get("bot", "channels").split(",")
        onStart = True
        db = MySQLdb.connect(host="localhost", user=db_user, passwd=db_passwd, db="pictures", charset='utf8')
        sqlcursor = db.cursor()
        #self.loger("%s --- %s" % (vk_user,vk_passwd) )
        
        self.loger("starting bot")
        t = threading.Thread(name = "Bot",target=self.recv_data, args=(sock,onStart,my_nick,defaultEncoding,channels,sqlcursor,db,))
        t.daemon = False
        t.start()

    def vkauth(self):
        global vkcookie,path,vkopener
        p = mp.current_process()
        istr = "add|%s|%s" % (p.name,p.pid)
        queue.put(istr)
        #self.loger("send login info")
        host = "vk.com"
        vkopener.addheaders = [('User-Agent', "Mozilla/5.0 (X11; Linux x86_64; rv:23.0) Gecko/20100101 Firefox/23.0"),
                       ('Accept','text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                       ('Accept-Language','en-US,en;q=0.5'),
                       ('Connection','keep-alive'),
                       ('host',host)]
        formdata = { "email" : self.vk_user, "pass": self.vk_passwd, "act" : "login", "role" : "al_frame" , "expire" : "", '_origin' : 'http://vk.com', 'captcha_key' : '',
            'captcha_sid' : '', 'ip_h' : '76b952d33e89ad7f4f','role' :'al_frame'}
        data_encoded = urllib.urlencode(formdata)
        self.loger(formdata)            
        url = "https://login.vk.com/?act=login"
        response = vkopener.open(url,data_encoded)
        #self.loger(response.read())
        vkcookie.save("%s/vk.txt" % path)
        istr = "del|%s|%s" % (p.name,p.pid)
        queue.put(istr)


    def processes1(self):
        o = "True"
        sys.stderr.write("watch dog started \n" )
        sys.stderr.flush()
        while o:
            try:
                istr = queue.get()
                if "add" in istr or "del" in istr :
                    args = istr.split("|")
                    #sys.stderr.write(" %s \n" % istr )
                    #sys.stderr.flush()
                    self.proces(args[0],args[1],args[2])
                else:  
                    sys.stderr.write(" %s \n" % istr )
                    sys.stderr.flush()
            except Empty: pass

    def threadNumber(self,sock):
        #try:
            sys.stderr.write("thread watch started \n" )
            sys.stderr.flush()
            #QueueManager.register('get_queue')
            #m = QueueManager(address=('127.0.0.1', 50000), authkey='abracadabra')
            #m.connect()

            while True:
                items = []
                index = 0
                for i in self.dataProc:
                    if i.is_alive() == False:
                        del self.dataProc[index]
                    index += 1
                time.sleep(10)
                itemsCount = len(threading.enumerate())
                for x in threading.enumerate():
                    items.append(x.getName())
                name_string = str(items)
                del items[:]
                #f = open("%s/threads.html" % path,"a")
                #f.writelines("<font color=red>[%s] </font><font color=blue>%s</font><br />\n" \
                #    % (time.strftime("%d %m %Y %H:%M:%S"), name_string))
                #f.writelines("<font color=red>[%s] </font><font color=blue>processes: %s</font><br />\n" \
                #    % (time.strftime("%d %m %Y %H:%M:%S"), str(self.dataProc)))
                #f.writelines("<font color=red>[%s] </font><font color=blue>processes:Processes %s</font><br />\n" \
                #    % (time.strftime("%d %m %Y %H:%M:%S"), str(self.processes)))
                #f.close()
                #sock.send("NOTICE Gendalf :Thread count %s : %s \n\r" % (itemsCount,name_string))
        #except: self.loger("<font color=red >thread threadNumber is dead</font>")
    def recv_data(self,sock,onStart,my_nick,defaultEncoding,channels,sqlcursor,db):
        global threadLife

        while threadLife : 
            try: 
                recv_data = sock.recv(4096)
            except:
                threadLife = False
                print "error"
                sock.close()
                db.close()
                self.exterminate()
                #self.run()
                break
            if not recv_data:
                threadLife = False
                sock.close()
                print "error"
                self.exterminate()
                db.close()
                #self.run()
                break
            else :
                #print recv_data
                #sys.stdout.write(recv_data)
                t = threading.Thread( target=self.worker, args=(recv_data,onStart,sock,my_nick,defaultEncoding,channels,sqlcursor,db,))
                t.daemon = False
                t.setName("Data process")
                t.start()

                #vk = threading.Thread(target=self.vk_message, args=(sock,defaultEncoding,0))
                #vk.daemon = True
                #vk.setName("VK Message reader")
                #vk.start()
    
    def worker(self,text,onStart,sock,my_nick,defaultEncoding,channels,sqlcursor,db):
            #print text[:-2]
            #self.loger("trying to start bot : %s" % text[:-2])
            if text.find("PING :") == 0:
                self.loger("sending PONG")
                sock.send(u"%s\n\r" % (text.replace("PING", "PONG")))
            elif text.find("Global Users:") > 0 or text.find("global Users") > 0:
                if onStart == True:
                    onStart = False
                    #print "JOIN: "
                    charset = self.detect_encoding(text)
                    for channel in channels :
                        sock.send('JOIN %s \n\r' % channel)
                    #print "Connected"
                    sock.send("PRIVMSG nickserv :IDENTIFY YED35\n\r")
                    sock.send("PRIVMSG chanserv :halfop #trollsquad feiris\n\r")
                    self.loger("starting informer")
                    torrent = mp.Process(name= "torrent informer",target=self.informer,args=(sock,sqlcursor,db,defaultEncoding,))
                    torrent.daemon = True
                    #t.setName("informer")
                    torrent.start()
                    self.dataProc.append(torrent)
                    time.sleep(1)
                    self.loger("starting ping")
                    pingProcess = mp.Process(name= "ping process",target=self.send_ping, args=(sock,))
                    pingProcess.daemon = True
                    self.dataProc.append(pingProcess)
                    #t.setName("ping")
                    pingProcess.start()
                    time.sleep(1)
                    if(self.vk_user !='' and self.vk_passwd !=''):
                        self.loger("trying login to vk")
                        vk_thread = mp.Process(name= "VK authentification",target=self.vkauth)
                        vk_thread.daemon = True
                        #vk_thread.setName("VK authentification")
                        vk_thread.start()
                        self.dataProc.append(vk_thread)
                    time.sleep(1)
                    self.loger("trying to start thread")
                    t = threading.Thread(target=self.threadNumber, args=(sock,))
                    t.daemon = True
                    t.setName("threadNumber")
                    t.start()
                    
                    #self.dataProc.append(t)
                    #self.vk_message(sock,defaultEncoding,0)
                    #vk = threading.Thread(target=self.vk_message, args=(sock,defaultEncoding,0,sqlcursor,db))
                    #vk.daemon = True
                    #vk.setName("VK Message reader")
                    #vk.start()
    
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
                try: 
                    nick = self.get_nick(text)
                except:
                    nick = "py-ctcp"
                sock.send("NOTICE %s :VERSION Simple bot writen on python\n\r" % nick)
            elif "NICK" in text: pass
                #if get_nick(text) == my_nick:
                #    indx = text.rfind("NICK") + 6
                #    nick.setText(text[indx:])
                #    chat_box["RAW"].append("<font color=red>[%s] </font>\
                #        <font color=orange>Your nick is %s now</font>" \
                #        % (time.strftime("%H:%M:%S") ,text[indx:]))
    
            elif "PONG" in text: pass
    
            elif "PRIVMSG" in text: 
                t = threading.Thread(target=self.privmsg, args=(text,sock,sqlcursor,db,defaultEncoding,))
                t.daemon = True
                t.setName("privmsg")
                t.start()
            elif "NOTICE" in text:
            	t = threading.Thread(target=self.notice, args=(text,sock,sqlcursor,db,defaultEncoding,))
                t.daemon = True
                t.setName("notice")
                t.start()
            else: 
                print ("Received data: ",
                    text[:-2].decode(defaultEncoding).encode("utf-8"))
    
    def privmsg(self,text,sock,sqlcursor,db,defaultEncoding):
        #global base,dbl
        channel = self.get_channel(text)
        nick = self.get_nick(text)
        indx = text.rfind("PRIVMSG") + len(channel) + 8
        color = re.compile(r'([0-9]{1,2})')
        text = color.sub("",text)
        text = text.replace("","")
        charset = self.detect_encoding(text)
        sql = """INSERT INTO logs(id,datetime,channel,nick,text) VALUES (NULL,NULL,'%s','%s','%s')""" % (channel,nick,text[indx+2:].decode(charset)) 
        sqlcursor.execute(sql)
        db.commit()
        if charset != defaultEncoding and channel == "#trollsquad":
            sock.send("PRIVMSG %s :05%s say: %s ~desu~\n\r" % (channel,nick,text[indx+2:].decode(charset).encode(defaultEncoding)))
        #print "%s" % text[indx:]
        #HTTP_RE  = re.compile(r"(http:\/\/[^\s]+)")
        #print HTTP_RE.search(text)
        try:
            if IMAGE_RE.search(text) and not IGNORE_RE.search(text): 
                t = mp.Process(name= "image process",target=self.link,
                    args=(text,sqlcursor,db,sock,))
                t.daemon = False
                #t.setName("image")
                t.start()
                self.dataProc.append(t)
            elif HTTP_RE.search(text) and not IGNORE_RE.search(text):
                #print "#%s %s:%s" % (channel,nick,text)
                t = mp.Process(name= "http process",target=self.http_title,args=(text, channel,sock,sqlcursor,db,defaultEncoding,))
                t.daemon = True
                #t.setName("http")
                t.start()
                self.dataProc.append(t)
        except: pass
        
        if text[indx+2:][0:5] == "$last" : 
            sqlcursor.execute(""" SELECT id,topic,link,change_data FROM torrent WHERE changed = '1' """)
            ident = sqlcursor.fetchall()
            if ident != None :
                if channel == "#trollsquad" or channel == "#test" : 
                    for x in xrange(len(ident)):
                        sqlcursor.execute("""UPDATE torrent SET changed='0' WHERE id = '%s';""" % ident[x][0])
                        db.commit()
                        datetime = ident[x][3]
                        title_text = ident[x][1].encode(defaultEncoding)
                        title_link = ident[x][2]
                        try :
                            sock.send("PRIVMSG %s :Torrent %s changed. Link: 03%s %s ~desu~\n\r" % (channel,str(title_text),title_link,datetime))
                        except :
                            sock.send("PRIVMSG %s :Torrent changed. Link: 03%s %s ~desu~\n\r" % (channel,title_link,datetime))
                        finally :
                            time.sleep(1)
        if text[indx+2:][0:3] == "$np" : 
            self.vk_audio(sock,text,defaultEncoding,sqlcursor,db,"")
        if text[indx+2:][0:8] == "$vkstart" and nick == "Gendalf" : 
            vk = threading.Thread(target=self.vk_message, args=(sock,defaultEncoding,0,sqlcursor,db))
            vk.daemon = True
            vk.setName("VK Message reader")
            vk.start()
        if text[indx+2:][0:5] == "$kill" and nick == "Gendalf" : self.exterminate()


    def notice(self,text,sock,sqlcursor,db,defaultEncoding):
        #global base,dbl
        try:
            channel = "#trollsquad"
            nick = self.get_nick(text)
            indx = text.rfind("NOTICE") + len("Feiris") + 9
            color = re.compile(r'([0-9]{1,2})')
            text = color.sub("",text)
            text = text.replace("","").replace("\n","").replace("\r","")
            charset = self.detect_encoding(text)
            txt = text[indx:]
            #self.loger("nick:%s<br>\ntext:%s<br>\nindex:%s" % (nick,txt,indx))
            if "$np" in txt: 
                #self.vk_audio(sock,text,defaultEncoding,sqlcursor,db,"",vkopener,AUDIO_RE,True)
                t = mp.Process(name= "vk music process",target = self.vk_audio, args = (sock,text,defaultEncoding,sqlcursor,db,"",vkopener,AUDIO_RE,True))
                t.daemon = True
                #t.setName("informer")
                t.start()
                self.dataProc.append(t)
        except: pass


    def http_title_cycle(self,url) : 
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:23.0) Gecko/20100101 Firefox/23.0'}
        charset = ""
        title = ""
        for trying in xrange(100) :
            request = urllib2.Request(url, None, headers)
            res = urllib2.urlopen(request)
            data = res.read()
            sech = re.compile(r"<title>(.*)<\/title>", re.I).findall(data.replace("\n",""))
            try: 
                title = sech[0]
                charset = self.detect_encoding(sech[0])
                self.loger("url:%s <-> try:%s <-> charset:%s ---> title: %s" % (url,trying,charset,title))
                return charset,sech[0]
            except:
                if trying < 100 :
                #     self.http_title_cycle(url,trying + 1)
                    self.loger("url:%s <-> try:%s <-> charset:%s ---> title: %s" % (url,trying,charset,title))
                    time.sleep(5)
        serf.loger("url:%s <-> try:%s <-> charset:%s ---> title: %s" % (url,trying,charset,sech[0]))
        raw_charset = CHARSET_RE.findall(data)[0]
        if raw_charset == "windows-1251": charset = "cp1251"
        else : charset = raw_charset
        return charset,title   


    def http_title(self,text, channel,sock,sqlcursor,db,defaultEncoding,trying = 0):
            p = mp.current_process()
            istr = "add|%s|%s" % (p.name,p.pid)
            queue.put(istr)
            headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:23.0) Gecko/20100101 Firefox/23.0'}
            m = HTTP_RE.findall(text)
            indx = text.rfind("PRIVMSG") + len(channel) + 8
            #print "m=%s" % m
            for x in m:
                try:
                    url = x
                    #print "url: %s" % url
                    if VK_RE.search(url) :
                        vkcookie.load("%s/vk.txt" % path)
                        vkopener = urllib2.build_opener(urllib2.HTTPCookieProcessor(vkcookie))
                        host = "vk.com"
                        vkopener.addheaders = [('User-Agent', "Mozilla/5.0 (X11; Linux x86_64; rv:23.0) Gecko/20100101 Firefox/23.0"),
                       ('Accept','text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                       ('Accept-Language','en-US,en;q=0.5'),
                       ('Connection','keep-alive'),
                       ('host',host)]
                        res =vkopener.open(url)
                    else :
                        request = urllib2.Request(url, None, headers)
                        res = urllib2.urlopen(request)
                    #print res.headers
                    info = res.info()
                    #print info
                    mimetype = info.getmaintype()
                    ext = info.getsubtype()
                    m = SITE_RE.search(url)
                    site = m.group("site")
                    sqlcursor.execute("""SELECT `id` from `ignore` where `url` LIKE '%%%s%%' """ %  site)
                    #contentSize = res.headers['content-length']
                    identSite = sqlcursor.fetchone()
                    #self.loger("%s->%s" %(repr(site),identSite))
                    if mimetype != "image" and mimetype == "text" :
                        data = res.read()
                        sech = re.compile(r"<title>(.*)<\/title>", re.I).findall(data.replace("\n",""))
                        nick = self.get_nick(text)
                        try:
                        	charset = self.detect_encoding(sech[0])
                        except:
                            charset,sech[0] = self.http_title_cycle(url)
                        #self.loger(res.msg)
                        #self.loger(sech[0].decode(charset))
                        trying = 0
                        title_text = sech[0].decode(charset).replace("\n","").replace("\r","")
                        color = re.compile(r'([0-9]{1,2})')
                        title_text = color.sub("",title_text)
                        title_text_src = title_text.encode(defaultEncoding)
                        title_text = self.unescape(title_text.encode(defaultEncoding)) 

                        if len(title_text) > 300 : title_text = title_text[:300]
                        if text[indx+2:][0:5] != "$add " :
                            if channel == "#trollsquad" or channel == "#test" : sock.send("PRIVMSG %s :05%s ~desu~\n\r" \
                                                                            % (channel, title_text))
                        
                        else: 
                            sha512hash = sha512(title_text_src).hexdigest()
                            sqlcursor.execute("""SELECT id from torrent where topic_sha LIKE '%s' """ %  sha512hash)
                            ident = sqlcursor.fetchone()
                            if ident == None:
                                sql = """INSERT INTO torrent(id,nick,link,topic,topic_sha,changed,change_data) VALUES (NULL,'%s','%s','%s','%s','0',NULL)""" % (nick,url,title_text_src,sha512hash)
                                try :
                                    sqlcursor.execute(sql)
                                    db.commit()
                                except MySQLdb.Error, e: 
                                    if db:
                                       db.rollback()
                                    self.loger("Error %d: %s" % (e.args[0],e.args[1]))
                                if channel == "#trollsquad" or channel == "#test" : sock.send("PRIVMSG %s :Torrent 03%s was successfully added ~desu~\n\r" \
                                                                            % (channel, url ))
                            elif channel == "#trollsquad" or channel == "#test" : sock.send("PRIVMSG %s :05%s ~desu~\n\r" \
                                                                            % (channel, "torrent already exists" ))
                       
                        if VIDEO_RE.search(data) and YOUTUBE_RE.search(url):
                            
                            m = VIDEO_RE.search(data)
                            videoid = m.group("videoid")
                            sql = """INSERT INTO `video` (autor,videoid,title,viewed) SELECT * FROM (SELECT '%s','%s','%s','0') AS tmp WHERE NOT EXISTS (SELECT `videoid` FROM `video` WHERE `videoid` = '%s') LIMIT 1; """ \
                                                                                            % (nick,videoid,title_text,videoid)
                            try :
                                sqlcursor.execute(sql)
                                db.commit()
                            except MySQLdb.Error, e: 
                                if db:
                                   db.rollback()
                                #self.loger("Error %d: %s" % (e.args[0],e.args[1]))

                        res.close()
                    elif mimetype == "image" and identSite == None:
                        new_file = res.read()
                        f = StringIO.StringIO(new_file)
                        img = Image.open(f)
                        lut = [255 if x > 200 else 0 for x in xrange(256)]
                        #self.loger("res len:%s -> file len:%s" % (len(new_file),contentSize ) )
                        out = img.convert('L').point(lut, '1')
                        histogram = ",".join(str(i) for i in img.histogram())
                        md5hash = md5(f.getvalue()).hexdigest()
                        sha512hash = sha512(f.getvalue()).hexdigest()
                        m = md5(url.replace("/","_")).hexdigest()
                        imagePath = "%s/images/%s.%s" % (path,m,ext) 
                        #imagePath = "%s/images/%s" % (path,url.replace("/","_")) 
                        fullname = "%s.%s" % (m,ext)
                        sqlcursor.execute("""SELECT id from pics where md5 LIKE '%s' """ %  md5hash)
                        ident = sqlcursor.fetchone()
                        #sqlcursor.execute("SELECT id FROM `pics`")
                        #cnt = sqlcursor.rowcount - 100
                        #sqlcursor.execute("""SELECT id,histogram from pics LIMIT %s,100 """ % cnt)
                        #name = sqlcursor.fetchall()
                        #for ih in xrange(len(name)):
                        #    if ih+1 != len(name):
                        #        xh =  [int(ii) for ii in name[ih][1].split(",")][255]
                        #        for y in xrange( ih+1 , len(name) , 1 ):
                        #            iy = [int(ii) for ii in name[y][1].split(",")][255]
                        #            if (xh-iy) < 0:
                        #                diff = (-(xh-iy))
                        #            else: diff = (xh-iy)
                        #            if diff < 30  : 
                        #               ident = name[ih][0]
                        #self.loger(ident)
                        if ident == None:
                            #img.save("%s" % (imagePath))
                            new_file2 = open("%s" % imagePath, 'w+')
                            new_file2.write(new_file)
                            new_file2.close()
                            nick = self.get_nick(text)
                            sqlcursor.execute("INSERT INTO binary_data VALUES(NULL, %s,%s,%s)", (md5hash,f.getvalue(), fullname,))
                            sql = """INSERT INTO pics(id,name,path,autor,datetime,rating,md5,sha512,histogram) VALUES (NULL,'%s','%s','%s',NULL,'0','%s','%s','%s')""" % (fullname,imagePath,nick,md5hash,sha512hash,histogram) 
                            sqlcursor.execute(sql)
                            db.commit()
                        elif channel == "#trollsquad" or channel == "#test" : 
                            sqlcursor.execute("""SELECT `datetime`,`autor` FROM `pics` WHERE `id` LIKE '%s' """ % ident)
                            autorAndDate = sqlcursor.fetchone()
                            #self.loger(autorAndDate)
                            sock.send("PRIVMSG %s :04%s %s http://pictures.gendalf.info/file/%s/ uploaded by %s ~baka~\n\r" \
                                                                            % (channel, "[:]||||||[:]",autorAndDate[0],md5hash,autorAndDate[1]))
                        res.close()


                except URLError, e: 
                    if hasattr(e, 'reason'): 
                        txt = 'We failed to reach a server. Reason: %s' % e.reason
                        if channel == "#trollsquad" or channel == "#test" : sock.send("PRIVMSG %s :04%s ~baka~\n\r" \
                                                                            % (channel, self.unescape(txt)))
                        #print 'We failed to reach a server.'
                        #print 'Reason: ', e.reason
                    elif hasattr(e, 'code'): 
                        txt = 'The server couldn\'t fulfill the request. Error code: %s' % e.code
                        if channel == "#trollsquad" or channel == "#test" : sock.send("PRIVMSG %s :04%s ~baka~\n\r" \
                                                                            % (channel, self.unescape(txt)))
                        #print 'The server couldn\'t fulfill the request.'
                        #print 'Error code: ', e.code
            istr = "del|%s|%s" % (p.name,p.pid)
            queue.put(istr)
    
    
    
    def link(self, text,sqlcursor,db,sock):
        p = mp.current_process()
        istr = "add|%s|%s" % (p.name,p.pid)
        queue.put(istr)
        m = IMAGE_RE.findall(text)
        for x in m:
          try:  
            #sys.stderr.write(x[0])
            #sys.stderr.flush()
            channel = self.get_channel(text)
            url = x[0]
            #print "url: %s" % url
            headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:23.0) Gecko/20100101 Firefox/23.0'}
            if VK_RE.search(url) :
                        res =vkopener.open(url)
            else :
                        request = urllib2.Request(url, None, headers)
                        res = urllib2.urlopen(request)
            info = res.info()
            mimetype = info.getmaintype()
            ext = info.getsubtype()
            m = SITE_RE.search(url)
            site = m.group("site")
            sqlcursor.execute("""SELECT `id` from `ignore` where `url` LIKE '%%%s%%' """ %  site)
            identSite = sqlcursor.fetchone()
            if mimetype == "image" and identSite == None:
                new_file = res.read()
                f = StringIO.StringIO(new_file)
                #new_file2 = open(f.getvalue(),'w+')
                img = Image.open(f)
                lut = [255 if x > 200 else 0 for x in xrange(256)]
                out = img.convert('L').point(lut, '1')
                histogram = ",".join(str(i) for i in img.histogram())
                m = md5(url.replace("/","_")).hexdigest()
                md5hash = md5(f.getvalue()).hexdigest()
                sha512hash = sha512(f.getvalue()).hexdigest()
                fullname = "%s.%s" % (m,ext)
                imagePath = "%s/images/%s.%s" % (path,m,ext)
                sqlcursor.execute("""SELECT id from pics where md5 LIKE '%s' """ %  md5hash)
                #self.loger(md5hash)
                ident = sqlcursor.fetchone()
                #sqlcursor.execute("SELECT id FROM `pics`")
                #cnt = sqlcursor.rowcount -100
                #self.loger("count:%s" % cnt)
                #sqlcursor.execute("""SELECT id,histogram from pics LIMIT %s,100 """ % cnt)
                #name = sqlcursor.fetchall()
                #for ih in xrange(len(name)):
                #    if ih+1 != len(name):
                #        xh =  [int(ii) for ii in name[ih][1].split(",")][255]
                #        for y in xrange( ih+1 , len(name) , 1 ):
                #            iy = [int(ii) for ii in name[y][1].split(",")][255]
                #            if (xh-iy) < 0:
                #                diff = (-(xh-iy))
                #            else: diff = (xh-iy)
                #            if diff < 30  : 
                #               ident = name[ih][0]
                            #self.loger(diff)
                #self.loger(ident)
                
                if ident == None : 
                    #img.save("%s" % (imagePath))
                    new_file2 = open("%s" % imagePath, 'w+')
                    new_file2.write(new_file)
                    new_file2.close()
                    nick = self.get_nick(text)
                    sqlcursor.execute("INSERT INTO binary_data VALUES(NULL, %s,%s,%s)", (md5hash,f.getvalue(), fullname,))
                    sql = """INSERT INTO pics(id,name,path,autor,datetime,rating,md5,sha512,histogram) VALUES (NULL,'%s','%s','%s',NULL,'0','%s','%s','%s')""" % (fullname,imagePath,nick,md5hash,sha512hash,histogram)
                    self.loger(sql)
                    sqlcursor.execute(sql)
                    db.commit()
                elif channel == "#trollsquad" or channel == "#test" :
                   sqlcursor.execute("""SELECT `datetime`,`autor` FROM `pics` WHERE `id` LIKE '%s' """ % ident)
                   autorAndDate = sqlcursor.fetchone()
                   #self.loger(autorAndDate)
                   sock.send("PRIVMSG %s :04%s %s http://pictures.gendalf.info/file/%s/ uploaded by %s ~baka~\n\r" \
                                                                            % (channel, "[:]||||||[:]",autorAndDate[0],md5hash,autorAndDate[1]))
                res.close()
                f.close()
          except URLError, e: 
                    if hasattr(e, 'reason'): 
                        txt = 'We failed to reach a server. Reason: %s' % e.reason
                        if channel == "#trollsquad" or channel == "#test" : sock.send("PRIVMSG %s :04%s ~baka~\n\r" \
                                                                            % (channel, self.unescape(txt)))
                        #print 'We failed to reach a server.'
                        #print 'Reason: ', e.reason
                    elif hasattr(e, 'code'): 
                        txt = 'The server couldn\'t fulfill the request. Error code: %s' % e.code
                        if channel == "#trollsquad" or channel == "#test" : sock.send("PRIVMSG %s :04%s ~baka~\n\r" \
                                                                            % (channel, self.unescape(txt)))
        istr = "del|%s|%s" % (p.name,p.pid)
        queue.put(istr)
    
    def vk_audio(self,sock,text,defaultEncoding,sqlcursor,db,old_track,vkopener,AUDIO_RE,notice=False):
       # sock.send("NOTICE %s :stage 0: send info\n\r" % self.get_nick(text))
        p = mp.current_process()
        istr = "add|%s|%s" % (p.name,p.pid)
        queue.put(istr)
        host = "vk.com"
        vkopener.addheaders = [('User-Agent', "Mozilla/5.0 (X11; Linux x86_64; rv:23.0) Gecko/20100101 Firefox/23.0"),
                       ('Accept','text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                       ('Accept-Language','en-US,en;q=0.5'),
                       ('Connection','keep-alive'),
                       ('host',host)]
        nick = self.get_nick(text)
        sqlcursor.execute("""SELECT ident from vk_ident where nick LIKE '%s' """ %  nick)
        ident = sqlcursor.fetchone()
        #self.loger(ident)
        if ident == None: return None
        url = 'https://vk.com/%s' % ident
        res =vkopener.open(url)
        #sock.send("NOTICE %s :stage 1: open vk\n\r" % self.get_nick(text))
        info = res.info()
        mimetype = info.getmaintype()
        if notice :
            channel = "#trollsquad" 
        else:
            channel = self.get_channel(text)
        if mimetype != "image" and mimetype == "text" :
            data = res.read()
            #sock.send("NOTICE %s :stage 2: read vk\n\r" % self.get_nick(text))
            #self.loger(data)
            sech = AUDIO_RE.findall(data)
            CHR_RE = re.compile(r"(&#[0-9]+;)")
            #sock.send("NOTICE %s :stage 3: find text. array len: %s\n\r" % (self.get_nick(text),len(sech)))
            if len(sech) != 0:
                try:
                    charset = self.detect_encoding(sech[0])
                except:
                    charset = "utf-8"
                title_text = sech[0].decode(charset).replace("\n","").replace("\r","")
                color = re.compile(r'([0-9]{1,2})')
                title_text = color.sub("",title_text)
                title_text_src = title_text
                title_text = self.unescape(title_text.encode(defaultEncoding))
                chr_search = CHR_RE.findall(title_text)
                unescape = HTMLParser().unescape
                if len(chr_search) != 0:
                     sys.stderr.write("char array %s \n" % chr_search )
                     sys.stderr.flush()
                     for char in chr_search:
                         ctring = unescape(char).encode("utf-8")
                         title_text = title_text.replace(char,ctring)
                         sys.stderr.write("replace char %s -> %s \n" % (char,ctring)  )
                         sys.stderr.flush()
                         #title_text = title_text.replace("&#%s;" % char,chr(int(char)))
                #self.loger(title_text)
                if channel == "#trollsquad" : 
                    sock.send("PRIVMSG %s :%s now listening: 05%s ~desu~\n\r" % (channel,nick,title_text))
            else : sock.send("PRIVMSG %s :04%s %s ~desu~\n\r" % (channel,nick, "hears the voice conspiratorially cockroaches in his head"))
        istr = "del|%s|%s" % (p.name,p.pid)
        queue.put(istr)

    def vk_message(self,sock,defaultEncoding,old_id,sqlcursor,db):
     p = mp.current_process()
     istr = "add|%s|%s" % (p.name,p.pid)
     queue.put(istr)
     start = True
     while start :    
        time.sleep(3)
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:23.0) Gecko/20100101 Firefox/23.0'}
        url = 'http://vk.com/im?sel=c1'
        #url = 'https://vk.com/im?peers=4698310_253730801_92810264_7434263_4755760_4432531_18834314_c3&sel=c2'
        res =vkopener.open(url)
        info = res.info()
        mimetype = info.getmaintype()
        charset = "cp1251"
        channel = "#trollsquad"
        if mimetype != "image" and mimetype == "text" :
            data = res.read()
            #data1 = data.decode(charset).encode(defaultEncoding)
            #self.loger(data)
            m = VKMESSAGE_RE.findall(data)
            src_txt = m[len(m)-1]
            msgID = src_txt[0]
            if old_id != msgID:
                VKnick = src_txt[1].decode(charset).encode(defaultEncoding)
                txt = src_txt[2].decode(charset).encode(defaultEncoding).replace("<br>"," ").replace('</a>',"")
                txt = re.sub('<a href=".*" target="_blank">','',txt, flags=re.IGNORECASE)
                txtarr = []
                if len(txt) > 300 :
                    for x in range(0,len(txt),300):
                        txtarr.append(txt[x: x + 300])
                imgURL = src_txt[4].decode(charset).encode(defaultEncoding)
                if imgURL != "" : txt = "%s %s" % (txt,imgURL)
                txt = self.unescape(txt)
                sqlcursor.execute("""SELECT nick from vk_ident where name LIKE '%s' """ %  VKnick)
                ident = sqlcursor.fetchone()
                if ident != None: VKnick = ident[0].encode(defaultEncoding)
                self.loger("MSG ID=%s<br>NICK=%s<br>TEXT=%s<br>IMAGE=%s<br>ENCODING=%s" % (msgID,VKnick,txt,imgURL,charset) )
                if VKnick == "Gendalf" and txt == "vkstop" :
                    start = False
                    txt = "Stoping parser"
                if len(txtarr) == 0 and len(txt) > 0  and VKnick != "Feiris": sock.send("PRIVMSG %s :05vk:%s: %s \n\r" % (channel ,VKnick, txt ))
                elif len(txtarr) > 0 and VKnick != "Feiris": 
                    for x in xrange(len(txtarr)) : 
                        sock.send("PRIVMSG %s :05vk:%s: %s \n\r" % (channel ,VKnick, txtarr[x] ))
                        time.sleep(0.5)
                old_id = msgID
        time.sleep(3)
     istr = "del|%s|%s" % (p.name,p.pid)
     queue.put(istr)
        #self.vk_message(sock,defaultEncoding,msgID)
            

    def send_ping(self,sock):
            global threadLife
            p = mp.current_process()
            sys.stderr.write("%s started pid=%s \n" % (p.name,p.pid) )
            sys.stderr.flush()
            istr = "add|%s|%s" % (p.name,p.pid)
            #self.proces("add", p.name, p.pid)
            queue.put(istr)
            #queue.put("qwerty")
            while threadLife:
                try:
                    o = queue.get(timeout=0.3)
                    if o == "Terminate" : threadLife = False
                except Empty: pass
                finally:
                    time.sleep(10)
                    sock.send("PING :LAG%s\n\r" % time.time())
            istr = "del|%s|%s" % (p.name,p.pid)
            queue.put(istr)

    def informer(self,sock,sqlcursor,db,defaultEncoding):
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:23.0) Gecko/20100101 Firefox/23.0'}
        p = mp.current_process()
        sys.stderr.write("%s started pid=%s \n" % (p.name,p.pid) )
        sys.stderr.flush()
        istr = "add|%s|%s" % (p.name,p.pid)
        queue.put(istr)
        threadLife = True
        while threadLife:
            try:
                o = queue.get(timeout=0.3)
                if o == "Terminate" : threadLife = False
            except Empty: pass
            
            time.sleep(3600)
            sqlcursor.execute(""" SELECT link FROM torrent """)
            ident = sqlcursor.fetchall()
            if ident != None:
                for x in xrange(len(ident)):
                    try:
                        request = urllib2.Request(ident[x][0], None, headers)
                        res = urllib2.urlopen(request)
                        sech = re.compile(r"<title>(.*)<\/title>").findall(res.read().replace("\n",""))
                        charset = self.detect_encoding(sech[0])
                        title_text = sech[0].decode(charset).replace("\n","").replace("\r","")
                        color = re.compile(r'([0-9]{1,2})')
                        title_text = color.sub("",title_text)
                        #title_text = self.unescape(title_text)
                        if len(title_text) > 300 : title_text = title_text[:300]
                        sha512hash = sha512(title_text).hexdigest()
                        sqlcursor.execute("""SELECT topic_sha from torrent where link LIKE '%s' """ %  ident[x][0])
                        topic_hash = sqlcursor.fetchone()[0]
                        self.loger("%s=>%s" % (topic_hash,sha512hash))
                        if topic_hash != sha512hash : 
                            sqlcursor.execute("""UPDATE torrent SET changed='1',topic = '%s',topic_sha = '%s',change_data = NULL WHERE link = '%s';""" % (title_text,sha512hash,ident[x][0]))
                            db.commit()
                            #if time.strftime("%H") == "20" :
                            sock.send("PRIVMSG %s :Torrent %s changed. Link: 03%s ~desu~\n\r" % ("#trollsquad",str(title_text),ident[x][0]))

                        
                    except: pass #traceback.print_exception(Value,Trace, limit=5,file="%s/error.txt" % path)


                    #self.loger()
                    #self.http_title(str(ident[x][0]),"#test",sock,sqlcursor,db,defaultEncoding)
                    

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

    def loger(self, text):
        f = open("%s/log.html" % path,"a")
        #text = self.escape_html(text)
        f.writelines("<font color=red>[%s] </font><font color=blue>%s</font><br />\n" \
            % (time.strftime("%d %m %Y %H:%M:%S"), text))
        f.close()
    def unescape(self,text):
        text = text.replace("&quot;","\"")
        text = text.replace("&lt;","<")
        text = text.replace("&gt;",">")
        text = text.replace("&nbsp;"," ")
        text = text.replace("&iexcl;","¡")
        text = text.replace("&cent;","¢")
        text = text.replace("&pound;","£")
        text = text.replace("&curren;","¤")
        text = text.replace("&yen;","¥")
        text = text.replace("&brvbar;","¦")
        text = text.replace("&sect;","§")
        text = text.replace("&uml;","¨")
        text = text.replace("&copy;","©")
        text = text.replace("&ordf;","ª")
        text = text.replace("&laquo;","«")
        text = text.replace("&not;","¬")
        text = text.replace("&shy;","")
        text = text.replace("&reg;","®")
        text = text.replace("&macr;","¯")
        text = text.replace("&deg;","°")
        text = text.replace("&plusmn;","±")
        text = text.replace("&sup2;","²")
        text = text.replace("&sup3;","³")
        text = text.replace("&acute;","´")
        text = text.replace("&micro;","µ")
        text = text.replace("&para;","¶")
        text = text.replace("&middot;","·")
        text = text.replace("&cedil;","¸")
        text = text.replace("&sup1;","¹")
        text = text.replace("&ordm;","º")
        text = text.replace("&raquo;","»")
        text = text.replace("&frac14;","¼")
        text = text.replace("&frac12;","½")
        text = text.replace("&frac34;","¾")
        text = text.replace("&iquest;","¿")
        text = text.replace("&amp;","&")
        text = text.replace("&#39;","'")
        text = text.replace("&#33;","!")
        CHR_RE = re.compile(r"(&#?[0-9a-zA-Z]+;)")
        chr_search = CHR_RE.findall(text)
        unescape = HTMLParser().unescape
        if len(chr_search) != 0:
            for char in chr_search:
                ctring = unescape(char).encode("utf-8")
                text = text.replace(char,ctring)
                sys.stderr.write("replace char %s -> %s \n" % (char,ctring)  )
                sys.stderr.flush()
        return text


if __name__ == "__main__":
    daemon = MyDaemon('/tmp/elis.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()        
        elif 'stop' == sys.argv[1]:
            daemon.terminate()
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.terminate()
            daemon.restart()        
        elif 'terminate' == sys.argv[1]:
            daemon.terminate() 
        elif 'list' == sys.argv[1]:
            daemon.listProcesses()                 
        else:
            print "Unknown command"
            sys.exit(2)        
            sys.exit(0)        
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
