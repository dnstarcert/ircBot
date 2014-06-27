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

basePath = "%s/%s" % (path,'logs.db')
dbl = sqlite3.connect(basePath)
base = dbl.cursor()
base.execute('CREATE TABLE IF NOT EXISTS logs (id int(3) PRIMARY KEY NOT NULL UNIQUE,nick text,datetime timestamp,txt text)')
dbl.commit()

vkcookie = MozillaCookieJar()
vkcookie.load("%s/vk.txt" % path)
vkopener = urllib2.build_opener(urllib2.HTTPCookieProcessor(vkcookie))

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
        db_user=config.get("db", "user")
        db_passwd=config.get("db", "passwd")
        vk_user=config.get("vk", "email")
        vk_passwd=config.get("vk", "passwd")
        channels = config.get("bot", "channels").split(",")
        onStart = True
        db = MySQLdb.connect(host="localhost", user=db_user, passwd=db_passwd, db="pictures", charset='utf8')
        sqlcursor = db.cursor()
        if(vk_user !='' and vk_passwd !=''):
            self.vkauth(vk_user,vk_passwd)

        t = threading.Thread(target=self.recv_data, args=(sock,onStart,my_nick,defaultEncoding,channels,sqlcursor,db,))
        t.daemon = False
        t.setName("Read data")
        t.start()
        
    def vkauth(self,vk_user,vk_passwd):
        global vkcookie,path,vkopener
        host = "vk.com"
        vkopener.addheaders = [('User-Agent', "Mozilla/5.0 (X11; Linux x86_64; rv:23.0) Gecko/20100101 Firefox/23.0"),
                       ('Accept','text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                       ('Accept-Language','en-US,en;q=0.5'),
                       ('Connection','keep-alive'),
                       ('host',host)]
        formdata = { "email" : vk_user, "pass": vk_passwd, "act" : "login", "role" : "al_frame" , "expire" : "", '_origin' : 'http://vk.com', 'captcha_key' : '',
            'captcha_sid' : '', 'ip_h' : '6b952d33e89ad7f4f','role' :'al_frame'}
        data_encoded = urllib.urlencode(formdata)            
        url = "https://login.vk.com/?act=login"
        response = vkopener.open(url)
        vkcookie.save("%s/vk.txt" % path)

    
    
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
                #self.run()
                break
            if not recv_data:
                threadLife = False
                sock.close()
                print "error"
                db.close()
                #self.run()
                break
            else :
                #print recv_data
                #sys.stdout.write(recv_data)
                t = threading.Thread(target=self.worker, args=(recv_data,onStart,sock,my_nick,defaultEncoding,channels,sqlcursor,db,))
                t.daemon = True
                t.setName("Data process")
                t.start()
    
    def worker(self,text,onStart,sock,my_nick,defaultEncoding,channels,sqlcursor,db):
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
                sock.send("PRIVMSG nickserv :IDENTIFY tuturuuu\n\r")
                t = threading.Thread(target=self.informer,args=(sock,sqlcursor,db,defaultEncoding,))
                t.daemon = True
                t.setName("informer")
                t.start()
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
                t = threading.Thread(target=self.privmsg, args=(text,sock,sqlcursor,db,defaultEncoding,))
                t.daemon = True
                t.setName("privmsg")
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
        #print "%s" % text[indx:]
        #HTTP_RE  = re.compile(r"(http:\/\/[^\s]+)")
        #print HTTP_RE.search(text)
        try:
            if IMAGE_RE.search(text) and not IGNORE_RE.search(text): 
                t = threading.Thread(target=self.link,
                    args=(text,sqlcursor,db,sock,))
                t.daemon = False
                t.setName("image")
                t.start()
            elif HTTP_RE.search(text) and not IGNORE_RE.search(text):
                #print "#%s %s:%s" % (channel,nick,text)
                t = threading.Thread(target=self.http_title,args=(text, channel,sock,sqlcursor,db,defaultEncoding,))
                t.daemon = True
                t.setName("http")
                t.start()
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

    
    def http_title(self,text, channel,sock,sqlcursor,db,defaultEncoding,trying = 0):
            headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:23.0) Gecko/20100101 Firefox/23.0'}
            m = HTTP_RE.findall(text)
            indx = text.rfind("PRIVMSG") + len(channel) + 8
            #print "m=%s" % m
            for x in xrange(len(m)):
                try:
                    url = m[x]
                    #print "url: %s" % url
                    if VK_RE.search(url) :
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
                    identSite = sqlcursor.fetchone()
                    #self.loger("%s->%s" %(repr(site),identSite))
                    if mimetype != "image" and mimetype == "text" :
                        data = res.read()
                        #self.loger(data)
                        sech = re.compile(r"<title>(.*)<\/title>", re.I).findall(data.replace("\n",""))
                        nick = self.get_nick(text)
                        try:
                            charset = self.detect_encoding(sech[0])
                        except:
                            #self.loger(data)
                            if trying < 100 :
                                 self.http_title(text, channel,sock,sqlcursor,db,defaultEncoding,trying + 1)
                                 time.sleep(5)
                            raw_charset = CHARSET_RE.findall(data)[0]
                            if raw_charset == "windows-1251": charset = "cp1251"
                            else : charset = raw_charset
                        #self.loger(res.msg)
                        #self.loger(sech[0].decode(charset))
                        trying = 0
                        title_text = sech[0].decode(charset).replace("\n","").replace("\r","")
                        color = re.compile(r'([0-9]{1,2})')
                        title_text = color.sub("",title_text)
                        title_text_src = title_text
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
                                self.loger("Error %d: %s" % (e.args[0],e.args[1]))

                        res.close()
                    elif mimetype == "image" and identSite == None:
                        f = StringIO.StringIO(res.read())
                        img = Image.open(f)
                        md5hash = md5(f.getvalue()).hexdigest()
                        sha512hash = sha512(f.getvalue()).hexdigest()
                        m = md5(url.replace("/","_")).hexdigest()
                        imagePath = "%s/images/%s.%s" % (path,m,ext) 
                        #imagePath = "%s/images/%s" % (path,url.replace("/","_")) 
                        fullname = "%s.%s" % (m,ext)
                        sqlcursor.execute("""SELECT id from pics where md5 LIKE '%s' """ %  md5hash)
                        ident = sqlcursor.fetchone()
                        self.loger(ident)
                        if ident == None:
                            img.save("%s" % (imagePath))
                            nick = self.get_nick(text)
                            sql = """INSERT INTO pics(id,name,path,autor,datetime,rating,md5,sha512) VALUES (NULL,'%s','%s','%s',NULL,'0','%s','%s')""" % (fullname,imagePath,nick,md5hash,sha512hash) 
                            sqlcursor.execute(sql)
                            db.commit()
                        elif channel == "#trollsquad" or channel == "#test" : 
                            sqlcursor.execute("""SELECT `datetime`,`autor` FROM `pics` WHERE `md5` LIKE '%s' """ % md5hash)
                            autorAndDate = sqlcursor.fetchone()
                            self.loger(autorAndDate)
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
    
    
    
    def link(self, text,sqlcursor,db,sock):
        m = IMAGE_RE.findall(text)
        for x in xrange(len(m)):
          try:  
            channel = self.get_channel(text)
            url = m[x][0]
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
                f = StringIO.StringIO(res.read())
                img = Image.open(f)
                m = md5(url.replace("/","_")).hexdigest()
                md5hash = md5(f.getvalue()).hexdigest()
                sha512hash = sha512(f.getvalue()).hexdigest()
                fullname = "%s.%s" % (m,ext)
                imagePath = "%s/images/%s.%s" % (path,m,ext)
                sqlcursor.execute("""SELECT id from pics where md5 LIKE '%s' """ %  md5hash)
                #self.loger(md5hash)
                ident = sqlcursor.fetchone()
                #self.loger(ident)
                print ident
                if ident == None : 
                    img.save("%s" % (imagePath))
                    nick = self.get_nick(text)
                    sql = """INSERT INTO pics(id,name,path,autor,datetime,rating,md5,sha512) VALUES (NULL,'%s','%s','%s',NULL,'1','%s','%s')""" % (fullname,imagePath,nick,md5hash,sha512hash)
                    sqlcursor.execute(sql)
                    db.commit()
                elif channel == "#trollsquad" or channel == "#test" :
                   sqlcursor.execute("""SELECT `datetime`,`autor` FROM `pics` WHERE `md5` LIKE '%s' """ % md5hash)
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
    def send_ping(self,sock):
            global threadLife
            while threadLife:
                time.sleep(10)
                sock.send("PING :LAG%s\n\r" % time.time())
    def informer(self,sock,sqlcursor,db,defaultEncoding):
        global threadLife
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:23.0) Gecko/20100101 Firefox/23.0'}
        while threadLife:
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
        f.writelines("<font color=red>[%s] </font><font color=blue>%s</font><br />" \
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
        return text


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
