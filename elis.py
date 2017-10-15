#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
#
#

import transmissionrpc
import socket
import threading
import sys, inspect, os, tempfile, re, traceback, dns.resolver, ssl, procname, datetime, json, cgi, httplib, random
import os.path
import base64, urllib2, urllib
from urllib2 import Request, urlopen, URLError
from chardet.universaldetector import UniversalDetector
from urlparse import urlparse
import ConfigParser
import time
from daemon import Daemon
from PIL import Image
import string, StringIO
import MySQLdb
from hashlib import md5, sha512
import sqlite3
from cookielib import MozillaCookieJar
from cookielib import FileCookieJar
import multiprocessing as mp
from multiprocessing.managers import BaseManager
from Queue import Empty
from subprocess import Popen, PIPE, check_output
from signal import SIGTERM
from HTMLParser import HTMLParser
import gzip
from setproctitle import setproctitle
import Pyro4, redis
from pyping import ping
from termcolor import colored, cprint
import psutil
try:
    import paramiko
except: 
    pass
import magic
from opensky_api import OpenSkyApi

# sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
os.chdir(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
threadLife = True
path = os.path.abspath(os.path.dirname(__file__))
CHANNEL_RE = re.compile('PRIVMSG (#?[\w\-]+) :')
NICK_RE = re.compile(":([\w\-\[\]\|`]+)!")
IDENT_RE = re.compile("!.?([\w\-\[\]\|`\.]+)@")
IMAGE_RE = re.compile(r"((ht|f)tps?:\/\/[\w\.-]+\/[\w\.-\/^,]+\.(jpg|png|gif|bmp))")
HTTP_RE = re.compile(r"(https?:\/\/[^\s^,]+)")
HTTPS_RE = re.compile(r"(https):\/\/[^\s^,]+")
PROXY_HOSTS_RE = re.compile(r"([^\s^,]+\.(ru|space|mobi|pw|ws|tw|pt|site|co|cu|com|info|net|org|gov|edu|int|mil|biz|to|pp|ne|msk|spb|nnov|od|in|ho|cc|dn|i|tut|v|eu|cy|tv|au|club|dp|sl|ddns|livejournal|herokuapp|azurewebsites|vip|xyz|me|top|biz|ua|kz|online|pro|click|website|bid))+ ")
IGNORE_RE = re.compile(r"(https?:\/\/pictures.gendalf.info)")
VIDEO_RE = re.compile(r"\'VIDEO_ID\': \"(?P<videoid>[\w\-\.]+?)\"")
YOUTUBE_RE = re.compile(r"(https?:\/\/www.youtube.com)")
SITE_RE = re.compile(r"(?P<site>https?:\/\/[a-zA-Z0-9\.]+)")
VK_RE = re.compile(r"(https?:\/\/vk.com)")
LURK_RE = re.compile(r"(https?:\/\/lurkmore.to)")
CHARSET_RE = re.compile('text/html; charset=([\w\s\-].*)\">')
AUDIO_RE = re.compile('<a class="current_audio fl_l" .*><div class="label fl_l"><\/div>(.*)<\/a>')
VKMESSAGE_RE = re.compile(
    '<tr id="mess([0-9]+?)"[\d\s\S\D]+?<a href=".*" class="mem_link" target="_blank">(.+?)\
    <.*<div class="im_msg_text">(.*?)?<\/div>(.*<img src="(.+?)")?',
    re.UNICODE)
PID_RE = re.compile(r"freeman\s+([\d]+)?\s+")
#IP_RE = re.compile(r"\"([0-9\.]+)\"")
IP_RE = re.compile(r"(?:25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9])(?:\.(?:25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)){3}")
HOST_RE = re.compile(r"https?:\/\/([^\s^,^\/]+)")
RUS_HOST_RE = re.compile(r"(https?:\/\/)([^\s^,^\/]+)")
FULLHOST_RE = re.compile(r"(?P<type>https?:\/\/)(?P<addr>[^\s^,^\/]+)(?P<content>\/.*)")
basePath = "%s/%s" % (path, 'logs.db')
dbl = sqlite3.connect(basePath)
base = dbl.cursor()
base.execute(
    'CREATE TABLE IF NOT EXISTS logs (id int(3) PRIMARY KEY NOT NULL UNIQUE,nick text,datetime timestamp,txt text)')
dbl.commit()
MUSIC_RE = re.compile('(np|listen|now playing)(:|»)(?P<content>.*)', re.I)

vkcookie = MozillaCookieJar()
vkcookie.load("%s/vk.txt" % path)
vkopener = urllib2.build_opener(urllib2.HTTPCookieProcessor(vkcookie))


import asyncore
import asynchat
import socket


class Lobby(object):
    def __init__(self):
        self.clients = set()

    def leave(self, client):
        self.clients.remove(client)

    def join(self, client):
        self.clients.add(client)

    def send_to_all(self, data):
        for client in self.clients:
            client.push(data)


class Client(asynchat.async_chat):
    def __init__(self, conn, lobby):
        asynchat.async_chat.__init__(self, sock=conn)
        self.in_buffer = ""
        self.set_terminator("n")

        self.lobby = lobby
        self.lobby.join(self)

    def collect_incoming_data(self, data):
        self.in_buffer += data

    def found_terminator(self):
        if self.in_buffer.rstrip() == "QUIT":
            self.lobby.leave(self)
            self.close_when_done()
        else:
            self.lobby.send_to_all(self.in_buffer + self.terminator)
            self.in_buffer = ""


class Server(asynchat.async_chat):
    def __init__(self):
        asynchat.async_chat.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(("0.0.0.0", 33333))
        self.listen(255)
        self.lobby = None

    def set_lobby(self, lobby):
        self.lobby = lobby

    def handle_accept(self):
        sock, addr = self.accept()
        client = Client(sock, self.lobby)


class QueueManager(BaseManager): pass


queue = mp.Queue()


# processes = dict()
class MyDaemon(Daemon):
    # class MyDaemon():

    vk_user = ""
    vk_passwd = ""
    uri = ""
    token = ""
    user_id = ""
    redisdb = ""
    ruboardName = ""
    ruboardPasswd = ""
    db = ""
    sqlcursor = ""
    proxyList = ""
    lobby = ""
    initialtime = datetime.datetime.now()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    defaultEncoding = ""
    my_nick = ""
    my_pass = ""
    mainpid = ''
    headers = [('User-Agent', "Mozilla/5.0 (X11; Linux x86_64; rv:36.0) Gecko/20100101 Firefox/41.0"),
               ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
               ('Accept-Language', 'en-US,en;q=0.5'),
               ('Connection', 'keep-alive')]

    def proces(self, doing, name, pid):
        # global processes
        # self.loger("action: %s => name : %s => pid: %s" % (doing,name,pid))
        if doing == "add":
            self.processes[name] = pid
        elif doing == "kill":
            self.processes[name].terminate()
        elif doing == "del":
            del self.processes[name]
        elif doing == "proxy":
            self.proxyList = name
            # sys.stderr.write(" %s \n" % self.processes )
            # sys.stderr.flush()

    def terminate(self):
        # global processes  str=`ps auxw | grep elis_rizon.py | awk ' {print $2 } '`
        # kill -9 $str
        pr = mp.current_process()
        print "my pid = %s" % pr.pid
        sys.stdout.write("killing child:")
        p = Popen(['ps', 'auxw'], stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        out = out.split('\n')
        for istr in out:
            if "elis_rizon" in istr:
                pid = int(PID_RE.match(istr).group(1))
                sys.stdout.write("%s " % pid)
                sys.stdout.flush()
                # print "\b%s " % pid
                # pid = int(istr.split(' ')[5])
                if int(pid) != int(pr.pid):
                    # print "pid = %s , kill = %s" % (pr.pid,pid)
                    os.kill(pid, SIGTERM)
                    time.sleep(0.1)
                    # print out,err
        for i in self.dataProc:
            i.terminate()
        for item in self.processes.values():
            item.terminate()

    def exterminate(self):
        pr = mp.current_process()
        pf = file('/tmp/elis_rizon.pid', 'r')
        pid = int(pf.read().strip())
        pf.close()

        for name, pid1 in self.processes.items():
            sys.stderr.write("killing process: %s ==> pid=%s\n" % (name, pid1))
            sys.stderr.flush()
            if int(pid1) != pid:
                os.kill(int(pid1), SIGTERM)
                time.sleep(0.1)
            else:
                os.remove('/tmp/elis_rizon.pid')
                os.kill(pid, SIGTERM)

    def listProcesses(self):
        # print self.processes
        # sys.stdout.flush()
        return self.processes

    # def start(self):
    #    self.run()

    def say(self, text):
        self.sock.send("PRIVMSG %s :%s ~desu~\n\r" % (text['channel'], text['text'].encode(self.defaultEncoding)))
        return "OK"

    def sendmsg(self, text):
        self.lobby.send_to_all("%s\n\r" % text)
        #telnetsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #telnetsock.connect(("0.0.0.0", 33333))
        #telnetsock.send("%s\n\r" % (text.encode("utf-8")))
        #telnetsock.close()

    def run(self):
        # print "daemon started"
        threadLife = True
        setproctitle("elis_rizon: main process")
        self.mainpid = mp.current_process().pid
        config = ConfigParser.RawConfigParser()
        config.read('%s/bot.cfg' % path)
        channels = config.get("bot", "channels").split(",")
        self.defaultEncoding = config.get("bot", "encoding")
        db_user = config.get("db", "user")
        db_passwd = config.get("db", "passwd")
        self.vk_user = config.get("vk", "email")
        self.vk_passwd = config.get("vk", "passwd")
        self.token = config.get("vk", "token")
        self.user_id = config.get("vk", "user")
        self.ruboardName = config.get("ruboard", "name")
        self.ruboardPasswd = config.get("ruboard", "passwd")
        self.db = MySQLdb.connect(host="localhost", user=db_user, passwd=db_passwd, db="pictures", charset='utf8')
        self.sqlcursor = self.db.cursor()
        p = mp.current_process()
        self.proces("add", p.name, p.pid)
        # self.loger(p)
        t = threading.Thread(target=self.processes1, args=())
        t.daemon = True
        t.setName("watch_dog")
        t.start()
        time.sleep(0.3)
        t1 = threading.Thread(target=self.processes2, args=())
        t1.daemon = True
        t1.setName("watch_dog_2")
        t1.start()
        time.sleep(0.3)
        pool = redis.ConnectionPool(host='localhost', port=6379, db=1)
        self.redisdb = redis.Redis(connection_pool=pool)
        self.lobby = Lobby()
        server = Server()
        server.set_lobby(self.lobby)
        t1 = threading.Thread(target=asyncore.loop, args=())
        t1.daemon = True
        t1.setName("asyncore")
        t1.start()
        self.connectToServer()


        # QueueManager.register('get_queue', callable=lambda:queue)
        # m = QueueManager(address=('127.0.0.1', 50000), authkey='abracadabra')
        # s = m.get_server()
        # s.serve_forever()

    def connectToServer(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock = sock
        config = ConfigParser.RawConfigParser()
        config.read('%s/bot.cfg' % path)
        NICK = config.get("bot", "nick")
        PASS = config.get("bot", "pass")
        HOST = config.get("bot", "server")
        PORT = config.get("bot", "port")
        self.my_nick = str(NICK).strip().rstrip()
        self.my_pass = str(PASS).strip().rstrip()
        my_nick = "NICK %s\n\r\n\r" % str(self.my_nick)
        sock.connect((HOST, int(PORT)))
        sock.send('CAP LS 302 \n\r\n\r')
        sock.send(my_nick)
        sock.send('USER Satori 95 * :Phantom \n\r\n\r')
        sock.send("USERHOST %s\n\r\n\r" % self.my_nick)
        sock.send('CAP REQ :away-notify chghost multi-prefix userhost-in-names\n\r\n\r')
        sock.send('CAP END\n\r\n\r')
        #recv_data = sock.recv(4096)
        #sys.stderr.write(recv_data)
        #sys.stderr.flush()
        sock.send("PRIVMSG nickserv :ghost %s %s\n\r\n\r" % (self.my_nick, self.my_pass))
        time.sleep(1)
        sock.send("PRIVMSG nickserv :release %s %s\n\r\n\r" % (self.my_nick, self.my_pass))
        time.sleep(.5)
        sock.send('PONG 123124124 \n\r\n\r')
        sock.send("NICK %s \n\r\n\r" % str(self.my_nick))
        # recv_data(sock)
        config = ConfigParser.RawConfigParser()
        config.read('%s/bot.cfg' % path)
        channels = config.get("bot", "channels").split(",")
        onStart = True
        # self.loger("%s --- %s" % (vk_user,vk_passwd) )
        myconf = {}  # тут должны быть все переменные передающиеся в функции
        # self.loger("starting bot")
        # self.defaultEncoding = defaultEncoding
        # while True :
        #    #try: 
        #        recv_data = self.sock.recv(4096)
        #        sys.stderr.write("RAW:%s" % recv_data )
        #        sys.stderr.flush()
        ##time.sleep(15)
        t = threading.Thread(name="Bot", target=self.recv_data,
                             args=(sock, onStart, my_nick, self.defaultEncoding, channels,))
        t.daemon = False
        t.start()

    def test_db_connection(self):
        global threadLife
        config = ConfigParser.RawConfigParser()
        config.read('%s/bot.cfg' % path)
        db_user = config.get("db", "user")
        db_passwd = config.get("db", "passwd")
        baseStatus = True
        # self.db = MySQLdb.connect(host="localhost", user=db_user, passwd=db_passwd, db="pictures", charset='utf8')
        # self.sqlcursor = self.db.cursor()
        while threadLife:
            try:
                self.sqlcursor.execute("""SHOW STATUS WHERE `Variable_name` = 'Aborted_connects'; """)
                status = self.sqlcursor.fetchone()
                if not status:
                    text = colored('MySQL Status : FAIL', 'yellow', attrs=['blink'])
                    self.db = MySQLdb.connect(host="localhost", user=db_user, passwd=db_passwd, db="pictures",
                                              charset='utf8')
                    self.sqlcursor = self.db.cursor()
                else:
                    if not baseStatus:
                        self.lobby.send_to_all("\033[34mMySQL Status : OK\033[0m\n\r")
                        baseStatus = True
            except:
                text = colored('MySQL Status : OFFLINE', 'red', attrs=['blink'])
                self.lobby.send_to_all("%s\n\r" % text)
                try:
                    self.db = MySQLdb.connect(host="localhost", user=db_user, passwd=db_passwd, db="pictures",
                                              charset='utf8')
                    self.sqlcursor = self.db.cursor()
                    baseStatus = False
                except:
                    pass
            time.sleep(30)
        sys.stderr.write("Thread DEAD \n")
        sys.stderr.flush()

    def vkauth(self):
        global vkcookie, path, vkopener
        p = mp.current_process()
        setproctitle("elis_rizon: vk authentification")
        greeting_maker = Pyro4.Proxy(self.uri)
        greeting_maker.proces("add", p.name, p.pid)
        # self.loger("send login info")
        host = "vk.com"
        vkopener.addheaders = [('User-Agent', "Mozilla/5.0 (X11; Linux x86_64; rv:36.0) Gecko/20100101 Firefox/36.0"),
                               ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                               ('Accept-Language', 'en-US,en;q=0.5'),
                               ('Connection', 'keep-alive'),
                               ('host', host)]
        # formdata = { "email" : self.vk_user, "pass": self.vk_passwd, "act" : "login", "role" : "al_frame" , "expire" : "", '_origin' : 'https://vk.com', 'captcha_key' : '',
        #    'captcha_sid' : '', 'ip_h' : '76b952d33e89ad7f4f','role' :'al_frame','lg_h':'569e29e911372b69b3','action':'https://login.vk.com/'}
        formdata = {'action': "https://login.vk.com/", 'act': 'login', 'to': '', '_origin': 'https://vk.com',
                    'ip_h': '76b952d33e89ad7f4f', 'lg_h': '0995ca2e30061c1572', 'email': self.vk_user,
                    'pass': self.vk_passwd}  # ,
        # 'role':'fast','no_redirect':'1','s':'0' }
        data_encoded = urllib.urlencode(formdata)
        # self.loger(formdata)
        # url = "http://vk.com/login.php?"
        #url = 'https://vk.com/login.php?act=login&role=fast&no_redirect=1&to=&s=0'
        #response = vkopener.open(url, data_encoded)
        # self.loger(response.read())
        #
        # vkcookie.save("%s/vk.txt" % path)
        # formdata = { "action" : "dologin ", "inmembername" : self.ruboardName, "inpassword": self.ruboardPasswd,"ref" : "http://forum.ru-board.com/board.cgi"}
        # data_encoded = urllib.urlencode(formdata)
        data_encoded = self.ruboardName
        url = "http://forum.ru-board.com/misc.cgi"
        response = vkopener.open(url, data_encoded)
        # self.loger(response.read())
        vkcookie.save("%s/vk.txt" % path)
        greeting_maker.proces("del", p.name, p.pid)

    def processes1(self):
        o = "True"
        sys.stderr.write("watch dog started \n")
        sys.stderr.flush()
        while o:
            try:
                istr = queue.get()
                if "add" in istr or "del" in istr:
                    args = istr.split("|")
                    self.proces(args[0], args[1], args[2])
                else:
                    sys.stderr.write(" %s \n" % istr)
                    sys.stderr.flush()
            except Empty:
                pass

    def processes2(self):
        greeting_maker = self
        listing_daemon = Pyro4.Daemon()
        self.uri = listing_daemon.register(greeting_maker)
        sys.stderr.write("Ready. Object uri =%s \n" % self.uri)
        sys.stderr.flush()
        setproctitle("elis_rizon: main process. uri = %s" % self.uri)
        listing_daemon.requestLoop()

    def redisCheck(self, sock, url, channel):
        if self.redisdb.exists(url):
            title_text = self.redisdb.get(url)
            if channel == "#trollsquad" or channel == "#test": sock.send("PRIVMSG %s :05%s \n\r" \
                                                                         % (channel, title_text))
            return True
        else:
            return False

    def threadNumber(self, sock):
        # try:
        sys.stderr.write("thread watch started \n")
        sys.stderr.flush()
        # QueueManager.register('get_queue')
        # m = QueueManager(address=('127.0.0.1', 50000), authkey='abracadabra')
        # m.connect()

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
            # f = open("%s/threads.html" % path,"a")
            # f.writelines("<font color=red>[%s] </font><font color=blue>%s</font><br />\n" \
            #    % (time.strftime("%d %m %Y %H:%M:%S"), name_string))
            # f.writelines("<font color=red>[%s] </font><font color=blue>processes: %s</font><br />\n" \
            #    % (time.strftime("%d %m %Y %H:%M:%S"), str(self.dataProc)))
            # f.writelines("<font color=red>[%s] </font><font color=blue>processes:Processes %s</font><br />\n" \
            #    % (time.strftime("%d %m %Y %H:%M:%S"), str(self.processes)))
            # f.close()
            # sock.send("NOTICE Gendalf :Thread count %s : %s \n\r" % (itemsCount,name_string))
            # except: self.loger("<font color=red >thread threadNumber is dead</font>")

    def recv_data(self, sock, onStart, my_nick, defaultEncoding, channels):
        global threadLife
        sqlcursor = self.sqlcursor
        db = self.db
        while True:
            try:
                recv_data = self.sock.recv(4096)
                # sys.stderr.write("RAW:%s" % recv_data )
                # sys.stderr.flush()
            except:
                threadLife = False
                print "socket error"
                sock.close()
                db.close()
                self.exterminate()
                # self.run()
                break
            if not recv_data:
                threadLife = False
                sock.close()
                print "no data. socket closed"
                self.exterminate()
                db.close()
                # self.run()
                break
            else:
                # print recv_data
                # sys.stdout.write(recv_data)
                self.initialtime = datetime.datetime.now()
                bold = re.compile(r'()')
                recv_data = bold.sub("", recv_data)
                color = re.compile(r'([0-9]{1,2})')
                recv_data = color.sub("", recv_data)
                underline = re.compile(r'()')
                recv_data = underline.sub("", recv_data)
                normal = re.compile(r'()')
                recv_data = normal.sub("", recv_data)
                t = threading.Thread(target=self.worker,
                                     args=(recv_data, onStart, sock, my_nick, defaultEncoding, channels,))
                t.daemon = False
                t.setName("Data process")
                t.start()

                # vk = threading.Thread(target=self.vk_message, args=(sock,defaultEncoding,0))
                # vk.daemon = True
                # vk.setName("VK Message reader")
                # vk.start()

    def worker(self, text, onStart, sock, my_nick, defaultEncoding, channels):
        # print text[:-2]
        # self.loger("trying to start bot : %s" % text[:-2])
        # print "RAW TEXT: %s \n" % text
        sqlcursor = self.sqlcursor
        db = self.db
        if text.find("PONG") == -1: self.lobby.send_to_all(text)
        # sys.stderr.write("RAW TEXT: %s \n" % text )
        # sys.stderr.flush()
        try:
            nick = self.get_nick(text)
        except:
            pass
        if text.find("PING :") == 0:
            self.loger("sending PONG")
            sock.send(u"%s\n\r" % (text.replace("PING", "PONG")))
        elif text.find("Global Users:") > 0 or text.find("global users") > 0:
            if onStart == True:
                onStart = False
                # print "JOIN: "
                # sock.send("VHOST vk lls39vj\n\r")
                sock.send("NICK %s \n\r" % str(self.my_nick))
                time.sleep(.5)
                sock.send("PRIVMSG nickserv :IDENTIFY %s\n\r" % self.my_pass)
                time.sleep(.5)
                sock.send("PROTOCTL NAMESX\n\r")
                sock.send("USERHOST %s\n\r" % self.my_nick)
                charset = self.detect_encoding(text)
                for channel in channels:
                    sock.send('JOIN %s \n\r' % channel)
                # print "Connected"
                # self.loger(sock.recv(4096))
                sock.send("PRIVMSG chanserv :op #trollsquad %s\n\r" % self.my_nick)

                # self.loger(sock.recv(4096))
                # self.loger("starting informer")
                # torrent = mp.Process(name= "torrent informer",target=self.informer,args=(sock,sqlcursor,db,defaultEncoding,))
                # torrent.daemon = True
                # t.setName("informer")
                # torrent.start()
                # self.dataProc.append(torrent)
                # time.sleep(1)
                # self.loger("starting ping")
                pingProcess = mp.Process(name="ping_process", target=self.send_ping, args=(sock,))
                pingProcess.daemon = True
                self.dataProc.append(pingProcess)
                pingProcess.start()
                ping_pid = pingProcess.pid
                sys.stderr.write("PROCESS: %s \n" % ping_pid)
                sys.stderr.flush()
                # stoleNick = mp.Process(name= "ping process",target=self.stoleNick, args=(sock,))
                # stoleNick.daemon = True
                # self.dataProc.append(stoleNick)
                # stoleNick.start()
                proxyProcess = mp.Process(name="proxy_pac_update_process", target=self.updateProxyList, args=(ping_pid, self.uri, ))
                proxyProcess.daemon = True
                self.dataProc.append(proxyProcess)
                proxyProcess.start()
                time.sleep(1)
                if (self.vk_user != '' and self.vk_passwd != ''):
                    # self.loger("trying login to vk")
                    vk_thread = mp.Process(name="VK_authentification", target=self.vkauth)
                    vk_thread.daemon = True
                    # vk_thread.setName("VK authentification")
                    vk_thread.start()
                    self.dataProc.append(vk_thread)
                time.sleep(1)
                # self.loger("trying to start thread")
                t = threading.Thread(target=self.threadNumber, args=(sock,))
                t.daemon = True
                t.setName("threadNumber")
                t.start()
                t2 = threading.Thread(target=self.test_db_connection, args=())
                t2.daemon = True
                t2.setName("MySQLdb check")
                t2.start()
                time.sleep(0.3)
                apcProcess = mp.Process(name="apc_process", target=self.apc, args=(sock,))
                apcProcess.daemon = True
                self.dataProc.append(apcProcess)
                apcProcess.start()
                openskyProcess = mp.Process(name="opensky", target=self.flightradar, args=(sock,ping_pid, ))
                openskyProcess.daemon = True
                self.dataProc.append(openskyProcess)
                openskyProcess.start()
                time.sleep(1)
                # self.dataProc.append(t)
                # self.vk_message(sock,defaultEncoding,0)
                # vk = threading.Thread(target=self.vk_message, args=(sock,defaultEncoding,0,sqlcursor,db))
                # vk.daemon = True
                # vk.setName("VK Message reader")
                # vk.start()
                # sys.stderr.write("_INITIAL_ TEXT: %s \n" % text )
                # sys.stderr.flush()
        elif "JOIN :" in text:
            pass
        # sock.send("PRIVMSG %s :VERSION\n\r" % get_nick(recv_data))
        elif ":VERSION " in text:
            indx = text.rfind("VERSION")
            # print indx
            # print recv_data[indx:-3]
        elif " KICK #" in text:
            print "KICK"
            p = re.compile(r"( [a-zA-Z0-9].*) :")
            text2 = p.findall(text)[0]
            indx = text2.rfind("#")
            indx2 = text2[indx:].rfind(" ")
            indx3 = text.rfind(":")
            reason = text[indx3 + 1:]
            channel = text2[indx:indx + indx2]
            us_nick = text2[indx + indx2 + 1:]
            if us_nick == my_nick[5:-2]:
                sock.send('JOIN %s \n\r' % channel)
        elif "VERSION" in text:
            # chat_box.append(repr(recv_data.decode("cp1251")))
            try:
                nick = self.get_nick(text)
            except:
                nick = "py-ctcp"
            sock.send("NOTICE %s :VERSION Simple bot writen on python\n\r" % nick)
        elif "NICK" in text:
            nick = self.get_nick(text)
            if nick == my_nick:
                indx = text.rfind("NICK") + 6
                self.redisdb.set('nick', text[indx:].rstrip())
                # if get_nick(text) == my_nick:
                #
                #    nick.setText(text[indx:])
                #    chat_box["RAW"].append("<font color=red>[%s] </font>\
                #        <font color=orange>Your nick is %s now</font>" \
                #        % (time.strftime("%H:%M:%S") ,text[indx:])) : ping 52387482734817
        elif "PONG" in text:
            pass
        elif "PING" in text:
            pass
        # try:
        # nick = self.get_nick(text)
        # indx = text.rfind("PING") + 5
        # pong = long(str(time.time()).split(".")[0] ) - long(text[indx:indx+10])
        # self.lobby.send_to_all(">>PING: %s" % text[indx:])
        # reply = "NOTICE %s :PING %s\n\r" % (nick,pong)
        # sock.send(reply)
        # self.lobby.send_to_all("<<PONG: %s\n\r" % pong)
        # except: pass
        elif "TIME" in text:
            sock.send("PRIVMSG %s :TIME %s\n\r" % (
                self.get_nick(text), datetime.datetime.now().strftime("%a %b %d %H:%M:%S")))
            # sock.send("NOTICE %s :TIME %s\n\r" % (self.get_nick(text),datetime.datetime.now().strftime("%a %b %d %H:%M:%S") ) )
        elif "PRIVMSG" in text:
            t = threading.Thread(target=self.privmsg, args=(text, sock, sqlcursor, db, defaultEncoding,))
            t.daemon = True
            t.setName("privmsg")
            t.start()
        elif "NOTICE" in text:
            # sock.send("NOTICE %s :stage -2: Starting thread\n\r" % self.get_nick(text))
            t = threading.Thread(target=self.notice, args=(text, sock, sqlcursor, db, defaultEncoding,))
            t.daemon = True
            t.setName("notice")
            t.start()
        elif "AWAY :" in text:
            indx = text.rfind("AWAY :")
            reason = text[indx:-2]
            sock.send("PRIVMSG %s :15%s %s ~desu~\n\r" % ('#trollsquad',nick,reason))
        elif "AWAY" in text:
            sock.send("PRIVMSG %s :15%s back ~desu~\n\r" % ('#trollsquad',nick))
        elif "QUIT :" in text:
            mat = open("%s/mat" % path, "r").read().split('\n')
            secure_random = random.SystemRandom()
            sock.send("PRIVMSG %s :%s\n\r" % ('#trollsquad',secure_random.choice(mat)))
        else:
            # sys.stderr.write("Received data: ",
            #    text[:-2].decode(defaultEncoding).encode("utf-8"))
            sys.stderr.write("ELSE TEXT: %s \n" % text)
            sys.stderr.flush()

    def stoleNick(self, sock):
        setproctitle("elis_rizon: interceptor")
        while True:
            sock.send("NICK Feiris\n\r")
            if self.redisdb.get('nick') == "Feiris":
                sock.send("PRIVMSG nickserv :group Elis YED35\n\r")
                break
            time.sleep(60)

    def privmsg(self, text, sock, sqlcursor, db, defaultEncoding):
        # global base,dbl
        # sys.stderr.write("worker : %s \n" % text )
        # sys.stderr.flush()
        channel = self.get_channel(text)
        nick = self.get_nick(text)
        indx = text.rfind("PRIVMSG") + len(channel) + 8
        bold = re.compile(r'()')
        text = bold.sub("", text)
        color = re.compile(r'([0-9]{1,2})')
        text = color.sub("", text)
        underline = re.compile(r'()')
        text = underline.sub("", text)
        text = text.replace("", "").replace("'", "&#39;")
        charset = self.detect_encoding(text)
        sql = """INSERT INTO logs(id,datetime,channel,nick,text) VALUES (NULL,NULL,'%s','%s','%s')""" % (
            channel, nick, text[indx + 2:].decode(charset))
        sqlcursor.execute(sql)
        db.commit()
        # lenofstring = len(text[indx+2:].decode(charset).encode(defaultEncoding))
        # sys.stderr.write("-> %s <-\n" % repr(text[indx+2:-2]) )
        # sys.stderr.flush()
        if charset != defaultEncoding and channel == "#trollsquad" and charset != "TIS-620" and len(
                text[indx + 2:]) > 4 and text[indx + 2:-2] != '№':
            sock.send("PRIVMSG %s :05%s say(%s): %s~desu~\n\r" % (
                channel, nick, charset, text[indx + 2:].decode(charset).encode(defaultEncoding)))
        # print "%s" % text[indx:]
        # HTTP_RE  = re.compile(r"(http:\/\/[^\s]+)")
        # print HTTP_RE.search(text)
        color = re.compile(r'([0-9]{1,2})')
        text = color.sub("", text)
        text = text.replace("", "").replace("\n", "").replace("\r", "").replace("", '').replace('', '')
        try:
            if IMAGE_RE.search(text) and not IGNORE_RE.search(text) and not "ДРОН НЕ СМОТРИ" in text:
                t = mp.Process(name="image process", target=self.link,
                               args=(text, sqlcursor, db, sock,))
                t.daemon = False
                # t.setName("image")
                t.start()
                self.dataProc.append(t)
            elif HTTP_RE.search(text) and not IGNORE_RE.search(
                    text) and not "ДРОН НЕ СМОТРИ" in text and not "$dns" in text:
                # print "#%s %s:%s" % (channel,nick,text)
                t = mp.Process(name="http process", target=self.http_title,
                               args=(text, channel, sock, sqlcursor, db, defaultEncoding,))
                t.daemon = True
                # t.setName("http")
                t.start()
                self.dataProc.append(t)
        except:
            pass
        # if "300" in text and channel == "#trollsquad":
        #    sock.send("PRIVMSG %s :%s, Отсоси у тракториста ~desu~\n\r" % (channel,nick))
        # if "да" in text or "Да" in text and channel == "#trollsquad":
        #    sock.send("PRIVMSG %s :Пизда ~desu~\n\r" % (channel))
        # if "нет" in text or "Нет" in text and channel == "#trollsquad":
        #    sock.send("PRIVMSG %s :Пидора ответ ~desu~\n\r" % (channel))
        # if "юкуыефке" in text and nick == 'Gendalf' :
        #    daemon = MyDaemon('/tmp/elis_rizon.pid')
        #    daemon.terminate()
        #    daemon.restart()
        if text[indx + 2:][0:5] == "$last":
            sqlcursor.execute(""" SELECT id,topic,link,change_data FROM torrent WHERE changed = '1' """)
            ident = sqlcursor.fetchall()
            if ident != None:
                if channel == "#trollsquad" or channel == "#test":
                    for x in xrange(len(ident)):
                        sqlcursor.execute("""UPDATE torrent SET changed='0' WHERE id = '%s';""" % ident[x][0])
                        db.commit()
                        datetime = ident[x][3]
                        title_text = ident[x][1].encode(defaultEncoding)
                        title_link = ident[x][2]
                        try:
                            sock.send("PRIVMSG %s :Torrent %s changed. Link: 03%s %s ~desu~\n\r" % (
                                channel, str(title_text), title_link, datetime))
                        except:
                            sock.send("PRIVMSG %s :Torrent changed. Link: 03%s %s ~desu~\n\r" % (
                                channel, title_link, datetime))
                        finally:
                            time.sleep(1)
        if text[indx + 2:][0:3] == "$np":
            self.vk_audio(sock, text, defaultEncoding, sqlcursor, db, "")
        if text[indx + 2:][0:8] == "$vkstart" and nick == "Gendalf":
            vk = threading.Thread(target=self.vk_message, args=(sock, defaultEncoding, 0, sqlcursor, db))
            vk.daemon = True
            vk.setName("VK Message reader")
            vk.start()
        if text[indx + 2:][0:4] == "$dns":
            dns_t = threading.Thread(target=self.dns_resolv, args=(sock, text, channel))
            dns_t.daemon = True
            dns_t.setName("VK Message reader")
            dns_t.start()
        if text[indx + 2:][0:5] == "$kill" and nick == "Gendalf": self.exterminate()
        st = MUSIC_RE.search(text)
        if st:
            st = st.group('content')
            name = re.sub(r'[\[|\{]((\w|\s)*\W\S+(\w|\s)*)+[\}|\]].*', '', st)
            # self.loger(name)
            channel = self.get_channel(text)
            # name = text[indx+2:][4:-2]
            t = mp.Process(name="VK Audio search", target=self.audiosearch,
                           args=(sock, channel, name, defaultEncoding, 'memory'))
            t.daemon = True
            # t.setName("http")
            t.start()
            self.dataProc.append(t)

    def notice(self, text, sock, sqlcursor, db, defaultEncoding):
            # global base,dbl
        try:
            channel = "#trollsquad"
            nick = self.get_nick(text)
            indx = text.rfind("NOTICE") + len(self.my_nick) + 9
            color = re.compile(r'([0-9]{1,2})')
            text = color.sub("", text)
            text = text.replace("", "").replace("\n", "").replace("\r", "").replace("", '')
            charset = self.detect_encoding(text)
            txt = text[indx:]
            # sock.send("NOTICE %s :stage -1: Parsing command. Command is %s\n\r" % (self.get_nick(text), txt  ) )
            # self.loger("nick:%s<br>\ntext:%s<br>\nindex:%s" % (nick,txt,indx))
            if "$np" in txt:
                # self.vk_audio(sock,text,defaultEncoding,sqlcursor,db,"",vkopener,AUDIO_RE,True)
                t = mp.Process(name="vk music process", target=self.vk_audio,
                               args=(sock, text, defaultEncoding, sqlcursor, db, "", vkopener, AUDIO_RE, True))
                t.daemon = True
                # t.setName("informer")
                t.start()
                self.dataProc.append(t)
                # print "Start VK Thread"
            elif "$pac" in txt:
                sock.send("NOTICE %s :%s \n\r" % (nick, self.redisdb.get('proxylistcount')))  # self.proxyList) )
            elif "$get_audio_url" in txt:
                t = mp.Process(name="vk music process", target=self.vk_audio,
                               args=(sock, text, defaultEncoding, sqlcursor, db, "get_track", vkopener, AUDIO_RE, True))
                t.daemon = True
                # t.setName("informer")
                t.start()
                self.dataProc.append(t)
            elif "$ms" in txt:
                self.sock.send("%s %s :%s (%s) \n\r" % (
                    'NOTICE', nick, str(self.redisdb.get('track')).encode(defaultEncoding), self.redisdb.get('trackName')))
            #elif "$ups" in txt:
            #    self.apc(sock)
        except: pass

    def dns_resolv(self, sock, text, channel):
        # sock.send("PRIVMSG %s :05host %s \n\r" % (channel, text))
        host = re.compile(r"\$dns (.*)").findall(text)[0]
        first = re.compile(r"((ht|f)tps?:\/\/)").sub("", host)
        second = first.split("/")[0]
        host = second.decode("utf-8").encode('idna')
        url = host
        if not "ipv6" in url:
            answers = dns.resolver.query(host, 'A')
        else:
            answers = ['0']
        if str(answers[0]) != "0":
            sock.send("PRIVMSG %s :05host %s ip is %s\n\r" % (channel, host, str(answers[0])))

    def http_title_cycle(self, url):
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:36.0) Gecko/20100101 Firefox/36.0', \
                   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', \
                   'Accept-Language': 'en-US,en;q=0.5', \
                   'Connection': 'keep-alive'}
        charset = ""
        title = ""
        self.loger(url)
        for trying in xrange(100):
            request = urllib2.Request(url, None, headers)
            res = urllib2.urlopen(request)
            data = res.read()
            sech = re.compile(r"<title>(.*)<\/title>", re.I).findall(data.replace("\n", ""))
            try:
                title = sech[0]
                charset = self.detect_encoding(sech[0])
                self.loger("try-> url:%s <-> try:%s <-> charset:%s ---> title: %s" % (url, trying, charset, title))
                return charset, sech[0]
            except:
                self.loger("except-> url:%s <-> try:%s <-> charset:%s ---> title: %s" % (url, trying, charset, title))
                time.sleep(2)
        # self.loger("finalle-> url:%s <-> try:%s <-> charset:%s ---> title: %s" % (url,trying,charset,sech[0]))
        # raw_charset = CHARSET_RE.findall(data)[0]
        # if raw_charset == "windows-1251": charset = "cp1251"
        # else : charset = raw_charset
        self.loger("returned data {charset:'%s' , title:'%s}'" % (charset, title))
        return charset, title

    def httpKillThread(self, name, pid):
        t = threading.Thread(target=self.httpKill, args=(name, pid))
        t.daemon = False
        t.setName(name)
        t.start()

    def httpKill(self, name, pid):
        sys.stdout.write("start timer for %s \n" % name)
        sys.stdout.flush()
        self.lobby.send_to_all("\033[36mstart timer for %s\033[0m\n\r" % name)
        time.sleep(180)
        try:
            os.kill(pid, SIGTERM)
            sys.stderr.write("killing process: %s. pid = %s \n" % (name, pid))
            sys.stderr.flush()
            self.lobby.send_to_all("\033[31mkilling process: %s. pid = %s\033[0m\n\r" % (name, pid))
        except:
            pass

    def http_title(self, text, channel, sock, sqlcursor, db, defaultEncoding, trying=0):
        p = mp.current_process()
        # sock.send("PRIVMSG %s : у тракториста ~desu~\n\r" % (channel))
        greeting_maker = Pyro4.Proxy(self.uri)
        greeting_maker.proces("add", p.name, p.pid)
        # proxy = IP_RE.findall(open(path + "/proxy.pac","r").read())
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:41.0) Gecko/20100101 Firefox/41.0'}
        m = HTTP_RE.findall(text)
        indx = text.rfind("PRIVMSG") + len(channel) + 8
        # print "m=%s" % m
        for x in m:
            try:
                url = x
                useproxy = ""
                cachedurl = url
                if url[len(url) - 1:] == "/": cachedurl = url[:-1]
                if not "$new" in text:
                    if self.redisCheck(sock, cachedurl, channel): break
                pre_url = RUS_HOST_RE.findall(x)[0]
                url2 = "%s" % pre_url[1].decode("utf-8")  # http://xn--b1aelm.xn--p1ai/
                # url2 = url2.encode('idna')
                url2 = "%s%s" % (pre_url[0], url2.encode('idna'))
                url = re.sub(HOST_RE, url2, url)
                setproctitle("elis_rizon: parse from %s" % url)
                dt = datetime.datetime.now()
                enter_time = dt - self.initialtime
                # sys.stderr.write("start process \n") ;sys.stderr.flush()
                hhost = FULLHOST_RE.search(url)
                # sys.stderr.write("%s \n" % hhost);sys.stderr.flush()
                # if hhost.group("addr") == "nnm-club.me":
                #    host_type = hhost.group("type")
                #    content_string = hhost.group("content")
                # sys.stderr.write("content : %s \n" % content_string);sys.stderr.flush()
                #    url="%s%s%s" % (host_type,'ipv6.nnm-club.me',content_string)
                if HOST_RE.findall(url) > 0:
                    host = HOST_RE.findall(url)[0]
                    hhost = host.split(".")
                    domain = hhost[len(hhost) - 1]
                else:
                    host = url
                # sys.stderr.write("host:%s \n" % url)
                # sys.stderr.flush()
                if not "ipv6" in url:
                    try:
                        answers = dns.resolver.query(host, 'A')
                    except:
                        answers = ['0']
                        self.lobby.send_to_all("\033[32mNo Nameservers: All nameservers failed to answer the query %s\033[0m\n\r" % url)
                        sock.send("PRIVMSG %s :04No Nameservers: All nameservers failed to answer the query %s ~baka~\n\r" % (channel, url) )
                else:
                    answers = ['0']
                # sys.stderr.write("url:%s => A = %s \n" % (host,answers[0])) ;sys.stderr.flush()
                # sys.stderr.flush()
                # sys.stderr.write("check url \n") ;sys.stderr.flush()
                verify_status = ''
                greeting_maker.httpKillThread(url, p.pid)
                self.lobby.send_to_all("\033[32murl:%s\033[0m\n\r" % url)
                self.lobby.send_to_all("\033[32mIP:%s\033[0m\n\r" % str(answers[0]) )
                self.lobby.send_to_all("\033[32mHOST:%s\033[0m\n\r" % str(host))
                proxy_answer = ''
                if self.redisdb.hget('proxy', str(answers[0])) == "1" : proxy_answer = "IP"
                elif self.redisdb.hget('proxy', str(host)) == "1": proxy_answer = "HOST"
                else : proxy_answer = "None"
                self.lobby.send_to_all("\033[31mProxy:%s\033[0m\n\r" % proxy_answer)
                if len(HTTPS_RE.findall(url)) > 0:
                    if proxy_answer == "None":
                        try:
                            self.lobby.send_to_all("\033[32murl:%s\033[0m\n\r" % 'VERIFY CERTIFICATE')
                            verify_host = HOST_RE.findall(url)[0]
                            #self.lobby.send_to_all("\033[32mhost:%s\033[0m\n\r" % HTTPS_RE.findall(url) )
                            verify_request = httplib.HTTPSConnection(verify_host, 443)
                            #try:
                            verify_request.request("GET", "")
                            #except :
                            #    pass
                            self.lobby.send_to_all("\033[32m%s\033[0m\n\r" % 'Verify certificate: OK')
                            #verify_status = '03OK'
                        except (ssl.SSLError,ssl.CertificateError) as e:
                            #self.lobby.send_to_all("%s" % dir(e) )
                            if hasattr(e, 'reason'): verify_status = '04%s' % e.reason
                            else: verify_status = '04CertificateError: %s' % e.message
                            self.lobby.send_to_all("\033[32m%s\033[0m\n\r" % 'Verify certificate: FAIL')
                            sock.send("PRIVMSG %s :04%s ~baka~\n\r" % (channel,verify_status) )
                            verify_status = '04certificate verify failed'
                try:
                    if VK_RE.search(url):
                        vkcookie1 = MozillaCookieJar()
                        vkcookie1.load("%s/vk.txt" % path)
                        self.lobby.send_to_all("\033[32m%s\033[0m\n\r" % 'Load vk cookie')
                        vkopener1 = urllib2.build_opener(urllib2.HTTPCookieProcessor(vkcookie1))
                        host = "vk.com"
                        vkopener1.addheaders = [
                            ('User-Agent', "Mozilla/5.0 (X11; Linux x86_64; rv:41.0) Gecko/20100101 Firefox/41.0"),
                            ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                            ('Accept-Language', 'en-US,en;q=0.5'),
                            ('Connection', 'keep-alive'),
                            ('host', host)]
                        dt3 = datetime.datetime.now()
                        res = vkopener1.open(url)
                        self.lobby.send_to_all("\033[32m%s (%s)\033[0m\n\r" % ('Load content', dt3 - dt))
                        #vkcookie1.save("%s/vk_res.txt" % path)
                    # elif str(answers[0]) in proxy : pass
                    elif not proxy_answer == "None":
                        self.lobby.send_to_all("\033[32mUSE PROXY\033[0m\n\r")
                        proxy_handler = urllib2.ProxyHandler({'http': 'http://proxy.antizapret.prostovpn.org:3128',
                                                              'https': 'https://proxy.antizapret.prostovpn.org:3128'})
                        # https_sslv3_handler = urllib.request.HTTPSHandler(context=ssl.SSLContext(ssl.PROTOCOL_SSLv3))
                        # sys.stderr.write("url = %s \n" % url)
                        # sys.stderr.flush()
                        opener = urllib2.build_opener(proxy_handler)
                        urllib2.install_opener(opener)
                        opener.addheaders = self.headers
                        # sys.stderr.write("via antizapret \n") ;sys.stderr.flush()
                        dt3 = datetime.datetime.now()
                        res = opener.open(url)
                        useproxy = "06{proxy: antizapret}"
                        # break
                    elif domain == "i2p":
                        self.lobby.send_to_all("\033[32mUSE I2P\033[0m\n\r")
                        proxy_handler = urllib2.ProxyHandler({'http': '10.1.0.1:4444',
                                                              'https': '10.1.0.1:4444'})
                        opener = urllib2.build_opener(proxy_handler)
                        opener.addheaders = self.headers
                        dt3 = datetime.datetime.now()
                        res = opener.open(url)
                    else:
                        sys.stderr.write("Create opener for url: %s\n" % url);
                        sys.stderr.flush()

                        #httpopener = urllib2.build_opener(urllib2.HTTPCookieProcessor(vkcookie))
                        #httpopener.addheaders = self.headers
                        dt3 = datetime.datetime.now()
                        self.lobby.send_to_all("\033[32m%s (%s)\033[0m\n\r" % ('Load content', dt3 - dt))
                        # sys.stderr.write("normal \n") ;sys.stderr.flush()
                        #res = httpopener.open(url)
                        # sys.stderr.write("read data \n") ;sys.stderr.flush()
                        # sys.stderr.write("Parse result \n");sys.stderr.flush()
                        ctx = ssl.create_default_context()
                        ctx.check_hostname = False
                        ctx.verify_mode = ssl.CERT_NONE
                        opener = urllib2.build_opener(urllib2.HTTPSHandler(context=ctx))
                        opener.addheaders = [
                            ('User-Agent', "Mozilla/5.0 (X11; Linux x86_64; rv:41.0) Gecko/20100101 Firefox/41.0"),
                            ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                            ('Accept-Language', 'en-US,en;q=0.5'),
                            ('Connection', 'keep-alive'),
                        ]
                        res = opener.open(url)
                        #request = urllib2.Request(url, None, headers)
                        #res = urllib2.urlopen(request)
                        # print res.headers
                except URLError, e:
                    if hasattr(e, 'reason'):
                        txt = 'We failed to reach a server. Reason: %s' % e.reason
                        if channel == "#trollsquad" or channel == "#test": sock.send("PRIVMSG %s :04%s ~baka~\n\r" \
                                                                                     % (channel, txt) )
                        # print 'We failed to reach a server.'
                        # print 'Reason: ', e.reason
                    elif hasattr(e, 'code'):
                        txt = 'The server couldn\'t fulfill the request. Error code: %s' % e.code
                        if channel == "#trollsquad" or channel == "#test": sock.send("PRIVMSG %s :04%s ~baka~\n\r" \
                                                                                     % (channel,txt) )
                #except:
                #    sock.send("PRIVMSG %s :04%s ~baka~\n\r" % (channel, "Operation timed out"))
                #    break
                dt5 = datetime.datetime.now()
                self.lobby.send_to_all("\033[32m%s (%s)\033[0m\n\r" % ('Get content',dt5 - dt3))
                check_time = dt3 - dt
                open_time = dt5 - dt3
                info = res.info()
                # print info
                mimetype = info.getmaintype()
                ext = info.getsubtype()
                m = SITE_RE.search(url)
                site = m.group("site")
                sqlcursor.execute("""SELECT `id` from `ignore` where `url` LIKE '%%%s%%' """ % site)
                # contentSize = res.headers['content-length']
                identSite = sqlcursor.fetchone()
                # self.loger("%s->%s" %(repr(site),identSite))
                if mimetype != "image" and mimetype == "text":
                    sech = ''
                    data = res.read()
                    self.lobby.send_to_all(
                        "\033[92m%s %s\033[0m\n\r" % ('INFO:', res.info())
                                          )
                    magic_part = StringIO.StringIO(data)
                    mime = magic.from_buffer(magic_part.read(), mime=True)
                    self.lobby.send_to_all(
                        "\033[96m%s %s\033[0m\n\r" % ('MIME:', mime))
                    self.lobby.send_to_all("\033[35m%s %s\033[0m\n\r" % ('Content-Length:',len(data)))
                    if len(data) == 0 :
                        sock.send(
                            "PRIVMSG %s :04Empty response ~baka~\n\r" % channel)
                        break
                    prepare_part = StringIO.StringIO(data)

                    self.lobby.send_to_all("\033[35m%s %s\033[0m\n\r" % ('Part len:',prepare_part.len))
                    #if VK_RE.search(url): 
                    #	data = res.read(5000)
                    #else:
                    #    data = res.read(5000)
                    #self.lobby.send_to_all("\033[32m%s (len: %s -> %s)\033[0m\n\r" % ('Parse',len(data),res.headers['content-length']))
                    read_time = datetime.datetime.now() - dt5
                    dt4 = datetime.datetime.now()
                    part = ''
                    if prepare_part.len >= 5000:
                        part = prepare_part.read(5000)
                    else :
                        part = prepare_part.read(prepare_part.len)
                    self.lobby.send_to_all("\033[35m%s %s\033[0m\n\r" % ('Part len:',len(part)))
                    try:
                        if len(data) > 5000:
                            while len(part) < int(len(data)):
                                sech = re.compile(r"<title>(.+?)<\/title>", re.I | re.M | re.X).findall(part.replace("\n", ""))
                                self.lobby.send_to_all("\033[32m%s (%s from %s)\033[0m\n\r" % ('part size',len(part),len(data)))
                                if sech : break
                                else: part = part + prepare_part.read(5000)
                        else:
                            sech = re.compile(r"<title>(.+?)<\/title>", re.I | re.M | re.X).findall(part.replace("\n", ""))
                            self.lobby.send_to_all("\033[32m%s (%s from %s)\033[0m\n\r" % ('part size',len(part),len(data)))   
                    except:
                        if channel == "#trollsquad" or channel == "#test": sock.send(
                            "PRIVMSG %s :04Header 'content-length' not found. READ ALL ~baka~\n\r" % channel)
                        data = res.read()
                        sech = re.compile(r"<title>(.+?)<\/title>", re.I | re.M | re.X).findall(data.replace("\n", ""))
                    if 'gzip' in mime:
                        buf = StringIO.StringIO(data)
                        f = gzip.GzipFile(fileobj=buf)
                        data = f.read()
                        sech = re.compile(r"<title>(.+?)<\/title>", re.I | re.M | re.X).findall(data.replace("\n", ""))
                    nick = self.get_nick(text)
                    # title = sech[0]
                    charset_flag = ''
                    self.lobby.send_to_all("\033[32m%s (%s)\033[0m\n\r" % ('title',(sech)))
                    self.lobby.send_to_all("\033[32m%s (%s)\033[0m\n\r" % ('title',len(sech)))
                    try:
                        try:
                            self.lobby.send_to_all("\033[32m%s (%s)\033[0m\n\r" % ('Get encoding',dt4 - dt5))
                            charset2 = re.compile(r'charset=(?P<ch>[\w\-\d]*)', re.I).search(
                                info.get('Content-Type')).group('ch')
                            charset_flag = '03H'
                        except:
                            charset2 = ''
                        if charset2:
                            if charset2 == 'windows-1251':
                                charset2 = 'cp1251'
                            charset = charset2
                            title = sech[0]
                        else:
                            self.lobby.send_to_all("\033[32m%s\033[0m\n\r" % 'Detect encoding')
                            sys.stderr.write("detecting encoding \n");
                            sys.stderr.flush()
                            title = sech[0]
                            charset = self.detect_encoding(sech[0])
                            charset_flag = '03D'
                    except:
                        sys.stderr.write("detect encoding error \n");
                        sys.stderr.flush()
                        if channel == "#trollsquad" or channel == "#test": sock.send(
                            "PRIVMSG %s :04I can not determine the encoding of the page ~baka~\n\r" % channel)
                        f = open('%s/fuck.html' % (path),'w')
                        f.write(data)
                        f.close()
                        break
                        # charset,title = self.http_title_cycle(url)
                        # self.loger("except {url:'%s',charset:'%s',title:'%s'}" % (url,charset,title))
                    # self.loger(res.msg)
                    # self.loger(sech[0].decode(charset))
                    trying = 0
                    if LURK_RE.search(url): charset = 'utf-8'
                    title_text = title.decode(charset).replace("\n", "").replace("\r", "")
                    color = re.compile(r'([0-9]{1,2})')
                    title_text = color.sub("", title_text)
                    title_text_src = title_text.encode(defaultEncoding)
                    title_text = self.unescape(title_text.encode(defaultEncoding)).strip().rstrip()
                    dt2 = datetime.datetime.now()
                    parse_time = dt4 - dt5
                    delta1 = str(dt2 - dt).split(":")[2].split(".")
                    minutes = int(str(dt2 - dt).split(":")[1])
                    if int(delta1[0]) != 0:
                        delta = "%s.%s s" % (delta1[0], delta1[1][0:4])
                    else:
                        delta = "0.%s sec" % delta1[1][0:4]
                    if minutes != 0:
                        delta = "%s min %s" % (minutes, delta)
                    if len(title_text) > 300: title_text = title_text[:300]
                    if text[indx + 2:][0:5] != "$add ":
                        self.redisdb.set(cachedurl, '05[:]||||||[:] %s %s 04¦ 05%s' % (
                            datetime.datetime.now().strftime("%d-%m-%Y %H:%M"), nick, title_text))
                        self.redisdb.expire(cachedurl, 60 * 60 * 24)
                        delta2 = "enter: %s , check : %s ,open: %s , read : %s , parse : %s , full : % s" % (
                            enter_time, check_time, open_time, read_time, parse_time, delta)
                        sys.stdout.write("%s (%s) \n" % (url, delta2));
                        sys.stdout.flush()
                        if channel == "#trollsquad" or channel == "#test": sock.send(
                            "PRIVMSG %s :05%s {%s} (%s) %s %s ~desu~\n\r"
                            % (channel, title_text, charset_flag, delta, useproxy,verify_status))
                        self.lobby.send_to_all("\033[32m%s\033[0m\n\r" % title_text)
                    else:
                        sha512hash = sha512(title_text_src).hexdigest()
                        sqlcursor.execute("""SELECT id from torrent where topic_sha LIKE '%s' """ % sha512hash)
                        ident = sqlcursor.fetchone()
                        if ident == None:
                            sql = """INSERT INTO torrent(id,nick,link,topic,topic_sha,changed,change_data) VALUES (NULL,'%s','%s','%s','%s','0',NULL)""" % (
                                nick, url, title_text_src, sha512hash)
                            try:
                                sqlcursor.execute(sql)
                                db.commit()
                            except MySQLdb.Error, e:
                                if db:
                                    db.rollback()
                                self.loger("Error %d: %s" % (e.args[0], e.args[1]))
                            if channel == "#trollsquad" or channel == "#test": sock.send(
                                "PRIVMSG %s :Torrent 03%s was successfully added ~desu~\n\r" \
                                % (channel, url))
                        elif channel == "#trollsquad" or channel == "#test":
                            sock.send("PRIVMSG %s :05%s ~desu~\n\r" \
                                      % (channel, "torrent already exists"))
                    if VIDEO_RE.search(data) and YOUTUBE_RE.search(url):
                        m = VIDEO_RE.search(data)
                        videoid = m.group("videoid")
                        # sys.stderr.write(videoid)
                        # sys.stderr.flush()
                        sql = """INSERT INTO `video` (autor,videoid,title,viewed) SELECT * FROM (SELECT '%s','%s','%s','0') AS tmp WHERE NOT EXISTS (SELECT `videoid` FROM `video` WHERE `videoid` = '%s') LIMIT 1; """ \
                              % (nick, videoid, title_text, videoid)
                        try:
                            sqlcursor.execute(sql)
                            db.commit()
                        except MySQLdb.Error, e:
                            if db:
                                db.rollback()
                            self.loger("Error %d: %s" % (e.args[0], e.args[1]))
                    res.close()
                elif mimetype == "image" and identSite == None:
                    new_file = res.read()
                    f = StringIO.StringIO(new_file)
                    img = Image.open(f)
                    lut = [255 if x > 200 else 0 for x in xrange(256)]
                    # self.loger("res len:%s -> file len:%s" % (len(new_file),contentSize ) )
                    out = img.convert('L').point(lut, '1')
                    histogram = ",".join(str(i) for i in img.histogram())
                    md5hash = md5(f.getvalue()).hexdigest()
                    sha512hash = sha512(f.getvalue()).hexdigest()
                    m = md5(url.replace("/", "_")).hexdigest()
                    imagePath = "%s/images/%s.%s" % (path, m, ext)
                    # imagePath = "%s/images/%s" % (path,url.replace("/","_"))
                    fullname = "%s.%s" % (m, ext)
                    sqlcursor.execute("""SELECT id from pics where md5 LIKE '%s' """ % md5hash)
                    ident = sqlcursor.fetchone()
                    # sqlcursor.execute("SELECT id FROM `pics`")
                    # cnt = sqlcursor.rowcount - 100
                    # sqlcursor.execute("""SELECT id,histogram from pics LIMIT %s,100 """ % cnt)
                    # name = sqlcursor.fetchall()
                    # for ih in xrange(len(name)):
                    #    if ih+1 != len(name):
                    #        xh =  [int(ii) for ii in name[ih][1].split(",")][255]
                    #        for y in xrange( ih+1 , len(name) , 1 ):
                    #            iy = [int(ii) for ii in name[y][1].split(",")][255]
                    #            if (xh-iy) < 0:
                    #                diff = (-(xh-iy))
                    #            else: diff = (xh-iy)
                    #            if diff < 30  : 
                    #               ident = name[ih][0]
                    # self.loger(ident)
                    if ident == None:
                        # img.save("%s" % (imagePath))
                        new_file2 = open("%s" % imagePath, 'w+')
                        new_file2.write(new_file)
                        new_file2.close()
                        nick = self.get_nick(text)
                        self.redisdb.set(url,
                                         "04[:]||||||[:] %s http://pictures.gendalf.info/file/%s/ uploaded by %s" % (
                                             datetime.datetime.now().strftime("%d-%m-%Y %H:%M"), md5hash, nick))
                        sqlcursor.execute("INSERT INTO binary_data VALUES(NULL, %s,%s,%s)",
                                          (md5hash, f.getvalue(), fullname,))
                        sql = """INSERT INTO pics(id,name,path,autor,datetime,rating,md5,sha512,histogram) VALUES (NULL,'%s','%s','%s',NULL,'0','%s','%s','%s')""" % (
                            fullname, imagePath, nick, md5hash, sha512hash, histogram)
                        sqlcursor.execute(sql)
                        db.commit()
                    elif channel == "#trollsquad" or channel == "#test":
                        sqlcursor.execute("""SELECT `datetime`,`autor` FROM `pics` WHERE `id` LIKE '%s' """ % ident)
                        autorAndDate = sqlcursor.fetchone()
                        self.redisdb.set(url, "[:]||||||[:] %s http://pictures.gendalf.info/file/%s/ uploaded by %s" % (
                            autorAndDate[0], md5hash, autorAndDate[1]))
                        # self.loger(autorAndDate)
                        sock.send(
                            "PRIVMSG %s :04%s %s http://pictures.gendalf.info/file/%s/ uploaded by %s ~baka~\n\r" \
                            % (channel, "[:]||||||[:]", autorAndDate[0], md5hash, autorAndDate[1]))
                    res.close()
                elif info.getsubtype() == "x-bittorrent":
                    nick = self.get_nick(text)
                    self.loger(nick)
                    if nick == "Gendalf":
                        self.loger(url)
                        tc = transmissionrpc.Client('10.1.0.1', port=9091)
                        self.loger("connected")
                        torrent = tc.add_torrent(url)
                        self.loger(torrent)
                        sock.send("PRIVMSG %s :torrent file: %s\n\r" % (nick, str(torrent).encode(defaultEncoding)))
            except URLError, e:
                if hasattr(e, 'reason'):
                    txt = 'We failed to reach a server. Reason: %s' % e.reason
                    if channel == "#trollsquad" or channel == "#test": sock.send("PRIVMSG %s :04%s ~baka~\n\r" \
                                                                                 % (channel, self.unescape(txt)))
                    # print 'We failed to reach a server.'
                    # print 'Reason: ', e.reason
                elif hasattr(e, 'code'):
                    txt = 'The server couldn\'t fulfill the request. Error code: %s' % e.code
                    if channel == "#trollsquad" or channel == "#test": sock.send("PRIVMSG %s :04%s ~baka~\n\r" \
                                                                                 % (channel, self.unescape(txt)))
                    # print 'The server couldn\'t fulfill the request.'
                    # print 'Error code: ', e.code
        greeting_maker.proces("del", p.name, p.pid)

    def link(self, text, sqlcursor, db, sock):
        p = mp.current_process()
        greeting_maker = Pyro4.Proxy(self.uri)
        greeting_maker.proces("add", p.name, p.pid)
        m = IMAGE_RE.findall(text)
        for x in m:
            try:
                # sys.stderr.write(x[0])
                # sys.stderr.flush()
                channel = self.get_channel(text)
                url = x[0]
                setproctitle("elis_rizon: image parser from %s" % url)
                if self.redisCheck(sock, url, channel): break
                # print "url: %s" % url
                headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:36.0) Gecko/20100101 Firefox/36.0'}
                if VK_RE.search(url):
                    res = vkopener.open(url)
                else:
                    request = urllib2.Request(url, None, headers)
                    res = urllib2.urlopen(request)
                info = res.info()
                mimetype = info.getmaintype()
                ext = info.getsubtype()
                m = SITE_RE.search(url)
                site = m.group("site")
                sqlcursor.execute("""SELECT `id` from `ignore` where `url` LIKE '%%%s%%' """ % site)
                identSite = sqlcursor.fetchone()
                if mimetype == "image" and identSite == None:
                    new_file = res.read()
                    f = StringIO.StringIO(new_file)
                    # new_file2 = open(f.getvalue(),'w+')
                    img = Image.open(f)
                    lut = [255 if x > 200 else 0 for x in xrange(256)]
                    out = img.convert('L').point(lut, '1')
                    histogram = ",".join(str(i) for i in img.histogram())
                    m = md5(url.replace("/", "_")).hexdigest()
                    md5hash = md5(f.getvalue()).hexdigest()
                    sha512hash = sha512(f.getvalue()).hexdigest()
                    fullname = "%s.%s" % (m, ext)
                    imagePath = "%s/images/%s.%s" % (path, m, ext)
                    sqlcursor.execute("""SELECT id from pics where md5 LIKE '%s' """ % md5hash)
                    # self.loger(md5hash)
                    ident = sqlcursor.fetchone()
                    # sqlcursor.execute("SELECT id FROM `pics`")
                    # cnt = sqlcursor.rowcount -100
                    # self.loger("count:%s" % cnt)
                    # sqlcursor.execute("""SELECT id,histogram from pics LIMIT %s,100 """ % cnt)
                    # name = sqlcursor.fetchall()
                    # for ih in xrange(len(name)):
                    #    if ih+1 != len(name):
                    #        xh =  [int(ii) for ii in name[ih][1].split(",")][255]
                    #        for y in xrange( ih+1 , len(name) , 1 ):
                    #            iy = [int(ii) for ii in name[y][1].split(",")][255]
                    #            if (xh-iy) < 0:
                    #                diff = (-(xh-iy))
                    #            else: diff = (xh-iy)
                    #            if diff < 30  :
                    #               ident = name[ih][0]
                    # self.loger(diff)
                    # self.loger(ident)

                    if ident == None:
                        # img.save("%s" % (imagePath))
                        new_file2 = open("%s" % imagePath, 'w+')
                        new_file2.write(new_file)
                        new_file2.close()
                        nick = self.get_nick(text)
                        self.redisdb.set(url, "[:]||||||[:] %s http://pictures.gendalf.info/file/%s/ uploaded by %s" % (
                            datetime.datetime.now(), md5hash, nick))
                        self.redisdb.expire(url, 3600 * 24 * 7)
                        sqlcursor.execute("INSERT INTO binary_data VALUES(NULL, %s,%s,%s)",
                                          (md5hash, f.getvalue(), fullname,))
                        sql = """INSERT INTO pics(id,name,path,autor,datetime,rating,md5,sha512,histogram) VALUES (NULL,'%s','%s','%s',NULL,'0','%s','%s','%s')""" % (
                            fullname, imagePath, nick, md5hash, sha512hash, histogram)
                        # self.loger(sql)
                        sqlcursor.execute(sql)
                        db.commit()
                    elif channel == "#trollsquad" or channel == "#test":
                        sqlcursor.execute("""SELECT `datetime`,`autor` FROM `pics` WHERE `id` LIKE '%s' """ % ident)
                        autorAndDate = sqlcursor.fetchone()
                        self.redisdb.set(url, "[:]||||||[:] %s http://pictures.gendalf.info/file/%s/ uploaded by %s" % (
                            autorAndDate[0], md5hash, autorAndDate[1]))
                        # self.loger(autorAndDate)
                        sock.send(
                            "PRIVMSG %s :04%s %s http://pictures.gendalf.info/file/%s/ uploaded by %s ~baka~\n\r" \
                            % (channel, "[:]||||||[:]", autorAndDate[0], md5hash, autorAndDate[1]))
                    res.close()
                    f.close()
            except URLError, e:
                if hasattr(e, 'reason'):
                    txt = 'We failed to reach a server. Reason: %s' % e.reason
                    if channel == "#trollsquad" or channel == "#test": sock.send("PRIVMSG %s :04%s ~baka~\n\r" \
                                                                                 % (channel, self.unescape(txt)))
                    # print 'We failed to reach a server.'
                    # print 'Reason: ', e.reason
                elif hasattr(e, 'code'):
                    txt = 'The server couldn\'t fulfill the request. Error code: %s' % e.code
                    if channel == "#trollsquad" or channel == "#test": sock.send("PRIVMSG %s :04%s ~baka~\n\r" \
                                                                                 % (channel, self.unescape(txt)))
        greeting_maker.proces("del", p.name, p.pid)

    def vk_audio(self, sock, text, defaultEncoding, sqlcursor, db, old_track, vkopener, AUDIO_RE, notice=False):
        # sock.send("NOTICE %s :stage 0: send info\n\r" % self.get_nick(text))
        burning = datetime.datetime.now()
        p = mp.current_process()
        setproctitle("elis_rizon: %s" % p.name)
        #greeting_maker = Pyro4.Proxy(self.uri)
        #greeting_maker.proces("add", p.name, p.pid)
        host = "vk.com"
        vkopener.addheaders = [('User-Agent', "Mozilla/5.0 (X11; Linux x86_64; rv:36.0) Gecko/20100101 Firefox/36.0"),
                               ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                               ('Accept-Language', 'en-US,en;q=0.5'),
                               ('Connection', 'keep-alive'),
                               ('host', host)]
        nick = str(self.get_ident(text)).lower()
        sqlcursor.execute("""SELECT user_id from vk_ident where nick LIKE '%s' """ % nick)
        ident = int(sqlcursor.fetchone()[0])
        nick = self.get_nick(text)
        # sock.send("NOTICE %s :stage 1: Your ID is %s\n\r" % (self.get_nick(text),ident ) )
        if ident == None or ident == 0: return None
        # sock.send("NOTICE %s :stage 2: requesting music tag\n\r" % self.get_nick(text))
        url = 'https://vk.com/%s' % ident
        base_request = datetime.datetime.now()
        base_request_delta = str(base_request - burning).split(":")[2]
        url = "https://api.vk.com/method/status.get?user_id=%i&v=5.29&access_token=%s" % (ident, self.token)
        res = vkopener.open(url)
        info = res.info()
        mimetype = info.getsubtype()
        if notice:
            oldChannel = nick
            channel = "#trollsquad"
        else:
            channel = self.get_channel(text)
        if mimetype != "image" and mimetype == "json":
            data = json.loads(res.read())
            server_request = datetime.datetime.now()
            server_request_delta = str(server_request - base_request).split(":")[2]
            response = data['response']
            if response.has_key('audio'):
                audio = response['audio']
                title_text = "%s - %s" % (audio['artist'].encode("utf-8"), audio['title'].encode("utf-8"))
            else:
                sock.send("PRIVMSG %s :04%s %s ~desu~\n\r" % (
                    channel, nick, "hears the voice conspiratorially cockroaches in his head"))
                return 1
            if len(title_text) != 0 and old_track == "":
                recode_time = datetime.datetime.now()
                recode_time_delta = str(recode_time - server_request).split(":")[
                    2]  # (base=%s , server=%s , recode=%s , delta=%s) % (base_request_delta,server_request_delta,recode_time_delta,delta)
                delta = str(recode_time - burning).split(":")[2]
                if channel == "#trollsquad":
                    sock.send("PRIVMSG %s :%s now listening: 05%s ~desu~\n\r" % (channel, nick, title_text))
                self.audiosearch(sock, oldChannel, title_text, defaultEncoding, 'memory')
            elif old_track == "get_track":
                self.audiosearch(sock, oldChannel, title_text, defaultEncoding, notice)
                # sock.send("NOTICE %s :%s \n\r" % (nick,audio['url']) )
        #greeting_maker.proces("del", p.name, p.pid)

    def audiosearch(self, sock, channel, name, defaultEncoding, notice=False):
        p = mp.current_process()
        name = urllib.quote_plus(name.strip().rstrip())
        try:
            greeting_maker = Pyro4.Proxy(self.uri)
            greeting_maker.proces("add", p.name, p.pid)
        except:
            pass
        finally:
            url = 'https://api.vk.com/method/audio.search?access_token=%s&q=%s&count=1' % (self.token, name)
            headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:36.0) Gecko/20100101 Firefox/36.0', \
                       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', \
                       'Accept-Language': 'en-US,en;q=0.5', \
                       'Connection': 'keep-alive'}
            # self.loger(url)
            request = urllib2.Request(url, None, headers)
            res = urllib2.urlopen(request)
            info = res.info()
            mimetype = info.getsubtype()
            if notice:
                msgtype = "NOTICE"
            else:
                msgtype = "PRIVMSG"
            if mimetype == "json" and channel == "#trollsquad" or notice:
                data = json.loads(res.read())
                try:
                    response = data['response'][1]
                    if notice == 'memory':
                        self.redisdb.set('track', response['url'])
                        trackname = "%s - %s" % (
                            response['artist'].encode(defaultEncoding), response['title'].encode(defaultEncoding))
                        self.redisdb.set('trackName', trackname)
                    else:
                        self.sock.send("%s %s :%s \n\r" % (msgtype, channel, response['url'].encode(defaultEncoding)))
                except:
                    pass
                # self.sock.send("%s %s :%s ~baka~\n\r" % (msgtype,channel,"404 Not Found :(" ) )
        try:
            greeting_maker.proces("del", p.name, p.pid)
        except:
            pass

    def send_ping(self, sock):
        global threadLife
        p = mp.current_process()
        setproctitle("elis_rizon: ping")
        sys.stderr.write("%s started pid=%s \n" % (p.name, p.pid))
        sys.stderr.flush()
        greeting_maker = Pyro4.Proxy(self.uri)
        greeting_maker.proces("add", p.name, p.pid)
        while threadLife:
            try:
                o = queue.get(timeout=0.3)
                if o == "Terminate": threadLife = False
            except Empty:
                pass
            finally:
                time.sleep(10)
                sock.send("PING :%s\n\r" % str(time.time()).split(".")[0])
        greeting_maker.proces("del", p.name, p.pid)

    def informer(self, sock, sqlcursor, db, defaultEncoding):
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:36.0) Gecko/20100101 Firefox/36.0'}
        p = mp.current_process()
        setproctitle("elis_rizon: informer")
        sys.stderr.write("%s started pid=%s \n" % (p.name, p.pid))
        sys.stderr.flush()
        greeting_maker = Pyro4.Proxy(self.uri)
        greeting_maker.proces("add", p.name, p.pid)
        threadLife = True
        while threadLife:
            try:
                o = queue.get(timeout=0.3)
                if o == "Terminate": threadLife = False
            except Empty:
                pass

            time.sleep(3600)
            sqlcursor.execute(""" SELECT link FROM torrent """)
            ident = sqlcursor.fetchall()
            if ident != None:
                for x in xrange(len(ident)):
                    try:
                        request = urllib2.Request(ident[x][0], None, headers)
                        res = urllib2.urlopen(request)
                        sech = re.compile(r"<title>(.*)<\/title>").findall(res.read().replace("\n", ""))
                        charset = self.detect_encoding(sech[0])
                        title_text = sech[0].decode(charset).replace("\n", "").replace("\r", "")
                        color = re.compile(r'([0-9]{1,2})')
                        title_text = color.sub("", title_text)
                        # title_text = self.unescape(title_text)
                        if len(title_text) > 300: title_text = title_text[:300]
                        sha512hash = sha512(title_text).hexdigest()
                        sqlcursor.execute("""SELECT topic_sha from torrent where link LIKE '%s' """ % ident[x][0])
                        topic_hash = sqlcursor.fetchone()[0]
                        # self.loger("%s=>%s" % (topic_hash,sha512hash))
                        if topic_hash != sha512hash:
                            sqlcursor.execute(
                                """UPDATE torrent SET changed='1',topic = '%s',topic_sha = '%s',change_data = NULL WHERE link = '%s';""" % (
                                    title_text, sha512hash, ident[x][0]))
                            db.commit()
                            # if time.strftime("%H") == "20" :
                            sock.send("PRIVMSG %s :Torrent %s changed. Link: 03%s ~desu~\n\r" % (
                                "#trollsquad", str(title_text), ident[x][0]))


                    except:
                        pass  # traceback.print_exception(Value,Trace, limit=5,file="%s/error.txt" % path)


                    # self.loger()
                    # self.http_title(str(ident[x][0]),"#test",sock,sqlcursor,db,defaultEncoding)
        greeting_maker.proces("del", p.name, p.pid)

    def detect_encoding(self, line):
        try:
            u = UniversalDetector()
            u.feed(line)
            u.close()
            result = u.result
            if result['encoding']:
                if result['encoding'] == "ISO-8859-2":
                    charset = "cp1251"
                elif result['encoding'] == "ascii":
                    charset = "utf-8"
                elif result['encoding'] == "utf8":
                    charset = "utf-8"
                elif result['encoding'] == "windows-1251":
                    charset = "cp1251"
                elif result['encoding'].find("ISO-88") == 0:
                    charset = "cp1251"
                elif result['encoding'].find("windows") == 0:
                    charset = "cp1251"
                elif result['encoding'] == "MacCyrillic":
                    charset = "cp1251"
                else:
                    charset = result['encoding']
            return charset
        except:
            return "utf-8"

    def get_channel(self, line):
        # line: irc.shock-world.com 319
        return CHANNEL_RE.search(line).group(1)

    def get_nick(self, line):
        return NICK_RE.match(line).group(1)

    def get_ident(self, line):
        return IDENT_RE.search(line).group(1)

    def loger(self, text):
        f = open("%s/log.html" % path, "a")
        # text = self.escape_html(text)
        f.writelines("<font color=red>[%s] </font><font color=blue>%s</font><br />\n" \
                     % (time.strftime("%d %m %Y %H:%M:%S"), text))
        f.close()

    def unescape(self, text):
        text = text.replace("&quot;", "\"")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&nbsp;", " ")
        text = text.replace("&iexcl;", "¡")
        text = text.replace("&cent;", "¢")
        text = text.replace("&pound;", "£")
        text = text.replace("&curren;", "¤")
        text = text.replace("&yen;", "¥")
        text = text.replace("&brvbar;", "¦")
        text = text.replace("&sect;", "§")
        text = text.replace("&uml;", "¨")
        text = text.replace("&copy;", "©")
        text = text.replace("&ordf;", "ª")
        text = text.replace("&laquo;", "«")
        text = text.replace("&not;", "¬")
        text = text.replace("&shy;", "")
        text = text.replace("&reg;", "®")
        text = text.replace("&macr;", "¯")
        text = text.replace("&deg;", "°")
        text = text.replace("&plusmn;", "±")
        text = text.replace("&sup2;", "²")
        text = text.replace("&sup3;", "³")
        text = text.replace("&acute;", "´")
        text = text.replace("&micro;", "µ")
        text = text.replace("&para;", "¶")
        text = text.replace("&middot;", "·")
        text = text.replace("&cedil;", "¸")
        text = text.replace("&sup1;", "¹")
        text = text.replace("&ordm;", "º")
        text = text.replace("&raquo;", "»")
        text = text.replace("&frac14;", "¼")
        text = text.replace("&frac12;", "½")
        text = text.replace("&frac34;", "¾")
        text = text.replace("&iquest;", "¿")
        text = text.replace("&amp;", "&")
        text = text.replace("&#39;", "'")
        text = text.replace("&#33;", "!")
        CHR_RE = re.compile(r"(&#?[0-9a-zA-Z]+;)")
        chr_search = CHR_RE.findall(text)
        unescape = HTMLParser().unescape
        if len(chr_search) != 0:
            for char in chr_search:
                ctring = unescape(char).encode("utf-8")
                text = text.replace(char, ctring)
                sys.stderr.write("replace char %s -> %s \n" % (char, ctring))
                sys.stderr.flush()
        return text

    def updateProxyList(self, ping_pid, uri):
        self.lobby.send_to_all("\033[32m%s. main process uri: %s\033[0m\n\r" % ("UPDATE PROXY LIST PROCESS STARTED", uri))
        sys.stderr.write("%s. main process uri: %s \n" % ("UPDATE PROXY LIST PROCESS STARTED", uri))
        sys.stderr.flush()
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:36.0) Gecko/20100101 Firefox/36.0'}
        proc = mp.current_process()
        setproctitle("elis_rizon: update proxy list")
        sys.stderr.write("%s started pid=%s \n" % (proc.name, proc.pid))
        sys.stderr.flush()
        try:
            pf = open('/tmp/elis_proxy.pid', 'r')
            proxy_pid = int(pf.read().strip())
            os.kill(int(proxy_pid), SIGTERM)
            pf.close()
        except:
            pass
        pf = open('/tmp/elis_proxy.pid', 'w')
        pf.write(str(proc.pid))
        pf.close()
        info = ["Angel", "Angel|off"]
        timer = 0
        addata = ""
        check = True
        pyro = Pyro4.Proxy(uri)
        pyro.proces("add", proc.name, proc.pid)
        pyro.sendmsg("\033[35m%s\033[0m\n\r" % "UPDATE PROXY LIST PROCESS STARTED")
        # time.sleep(15)
        while check:
            if timer <= 0:
                try:
                    ddate = ""
                    diff1 = {}
                    diff2 = {}
                    dt = datetime.datetime.now()
                    request = urllib2.Request('https://antizapret.prostovpn.org/proxy.pac', None, headers)
                    try:
                        f = open(path + "/proxy.pac", "r+")
                        date = f.read()
                        ddate2 = date.split("\n")
                        for i in ddate2:
                            diff1[i.strip().rstrip()] = '1'
                        ddate = date.split("\n")[1].split(" on ")[1].strip().rstrip()
                        f.close()
                    except:
                        setproctitle("elis_rizon: update proxy list. error on read file ")
                    ddata = urllib2.urlopen(request).read()
                    ddata2 = ddata.split("\n")
                    for i in ddata2:
                        diff2[i.strip().rstrip()] = '1'
                    self.redisdb.delete('proxy')
                    dt_request = datetime.datetime.now()
                    # ff = open(path+'/prox','w')
                    total_ip = 0
                    total_hst = 0
                    for i in ddata2:
                        ip = IP_RE.findall(i)  # .strip().rstrip()#.replace('"','').replace(',','')
                        hst = PROXY_HOSTS_RE.findall(i)
                        # ff.write("%s => %s\r\n" % (ip,len(ip)))
                        if len(ip) > 0:
                            self.redisdb.hset('proxy', ip[0], 1)
                            total_ip += 1
                            # self.redisdb.lpush('proxy',*ip)
                        elif len(hst) > 0:
                            self.redisdb.hset('proxy', hst[0][0], 1)
                            total_hst += 1
                    # ff.close()
                    pyro.sendmsg("\033[32mTOTAL_IP:%s\033[0m" % str(total_ip))
                    pyro.sendmsg("\033[32mTOTAL_HOSTS:%s\033[0m" % str(total_hst))
                    #self.lobby.send_to_all("\033[32mTOTAL_IP:%s\033[0m\n\r" % str(total_ip))
                    #self.lobby.send_to_all("\033[32mTOTAL_HOSTS:%s\033[0m\n\r" % str(total_hst))
                    addata = ddata.split("\n")[1].split(" on ")[1].strip().rstrip()
                    dt_get_ip = datetime.datetime.now()
                    if ddate != addata:
                        text = colored('Found mutationes in proxy: update in database', 'cyan', attrs=['blink'])
                        pyro.sendmsg("%s" % str(text))
                        t = threading.Thread(target=self.update_proxy_thread, args=(ddata, pyro, ))
                        t.daemon = True
                        t.setName("update proxy thread")
                        t.start()
                        dt_diff_start = datetime.datetime.now()
                        try:
                            self.redisdb.delete('proxy_diff_add')
                            self.redisdb.delete('proxy_diff_del')
                        except:
                            pass
                        t = threading.Thread(target=self.get_proxy_diff,
                                             args=(diff1, diff2, 'proxy_diff_add', 'proxy_add', pyro, ))
                        t.daemon = True
                        t.setName("add ip")
                        t.start()
                        t = threading.Thread(target=self.get_proxy_diff,
                                             args=(diff2, diff1, 'proxy_diff_del', 'proxy_del', pyro, ))
                        t.daemon = True
                        t.setName("delete ip")
                        t.start()
                        time.sleep(1)
                        #while int(self.redisdb.get('proxy_add')) and int(self.redisdb.get('proxy_del')): pass
                        # for data1 in ddate2 :
                        #    if not data1 in ddata2:
                        #        diff1.append(data1)
                        # for data1 in ddata2 :
                        #    if not data1 in ddate2:
                        #        diff2.append(data1)
                        # diff2
                        total = str(self.redisdb.hlen('proxy'))
                        added = int(self.redisdb.hlen('proxy_diff_add')) - 1
                        deleted = int(self.redisdb.hlen('proxy_diff_del')) - 1
                        # sock.send("PRIVMSG %s :03proxy.pac modified: %s 12add:%s 04del:%s 06total IP's in blacklist = %s ~desu~\n\r" % (i,addata,added,deleted,total))
                        # sock.send("PRIVMSG %s :03proxy.pac modified: %s 02add:%s 04del:%s 10total IP's in blacklist = %s ~desu~\n\r" % ("#test",addata,added,deleted,total))
                        dt2 = datetime.datetime.now()
                        delta1 = str(dt2 - dt).split(":")[2].split(".")
                        minutes = int(str(dt2 - dt).split(":")[1])
                        if int(delta1[0]) != 0:
                            delta = "%s.%s s" % (delta1[0], delta1[1][0:4])
                        else:
                            delta = "0.%s sec" % delta1[1][0:4]
                        if minutes != 0:
                            delta = "%s min %s" % (minutes, delta)
                        delta_request = str(dt_request - dt).split(":")[2].split(".")
                        delta_get_ip = str(dt_get_ip - dt_request).split(":")[2].split(".")
                        delta_diff = str(dt2 - dt_diff_start).split(":")[2].split(".")
                        delta_all = "request: %s.%s s,get ip: %s.%s s,calculation of the difference: %s.%s s" % (
                            delta_request[0], delta_request[1][0:4], \
                            delta_get_ip[0], delta_get_ip[1][0:4], delta_diff[0], delta_diff[1][0:4])
                        q = "proxy|03proxy.pac modified: %s 02add:%s 04del:%s 10total IP's in blacklist = %s (%s,total:%s)~desu~|%s" % (
                            addata, added, deleted, total, delta_all, delta, proc.pid)
                        queue.put(q)
                        self.redisdb.set('proxylistcount', q.split('|')[1])
                        pyro.sendmsg("\033[32mProxy DIFF:\nAdd:%s\nDel:%s,\nTotal:%s\033[0m" % (
                            added, deleted, total
                                                                                               )
                                     )
                        # self.redisdb.expire(proxylist,60*60*3)
                    else:
                        text = colored('Mutationes lists per procuratorem praestari non inveni', 'yellow', attrs=['blink'])
                        pyro.sendmsg("%s" % str(text))
                    mod_time = time.ctime(os.path.getmtime(path + "/proxy.pac"))
                    setproctitle(
                        "elis_rizon: update proxy list. proxy.pac last modified: %s | check = %s" % (addata, check))
                    today = datetime.datetime.now()
                    update_delta = datetime.timedelta(hours=1)  # дельта в 2 дня
                    now_date = today + update_delta
                    next_update = datetime.datetime.now().replace(now_date.year, now_date.month, now_date.day,
                                                                  now_date.hour, 8, 0)
                    update_delta = next_update - today
                    timer = update_delta.seconds  # 18000
                    del diff1
                    del diff2
                    # timer = 60*2
                except:
                    setproctitle("elis_rizon: update proxy list. request section error")
                    time.sleep(60)
                    sys.stderr.write("ERROR TEXT: update proxy list. request section error \n")
                    sys.stderr.flush()
            try:
                if psutil.pid_exists(int(ping_pid)):
                    pass
                else:
                    os.kill(int(proc.pid), SIGTERM)
            except:
                setproctitle("elis_rizon: update proxy list. error on psutil section")
                sys.stderr.write("ERROR TEXT: update proxy list. error on psutil section \n")
                sys.stderr.flush()
            time.sleep(60)
            timer -= 60
            setproctitle("elis_rizon: update proxy list. proxy.pac last modified: %s. next update after %s seconds " % (
                addata, timer))


    def update_proxy_thread(self, ddata, pyro):
        ff = open(path + "/proxy.pac", "w+")
        ff.write(ddata)
        ff.close()
        try:
            ff = open("/var/www/localhost/htdocs/proxy.pac", "w+")
            ff.write(ddata)
            ff.close()
            #ff = open("/home/freeman/pybot/images/cloud/owncloud/proxy.pac", "w+")
            #ff.write(ddata)
            #ff.close()
        except:
            text = colored('UPDATE PROXY LIST FAILED', 'red', attrs=['blink'])
            pyro.sendmsg("%s" % str(text))

    def get_proxy_diff(self, ddate2, ddata2, diff, name, pyro):
        self.redisdb.set(name, '1')
        dt = datetime.datetime.now()
        pyro.sendmsg("\033[34mget proxy diff thread. mode: %s started.\033[0m" % str(name))
        log = ''
        for i in ddate2.keys():
            if not i in ddata2:
                self.redisdb.hset(diff, i, i)
                if name == 'proxy_add':
                    log = " - %s" % i
                    #pyro.sendmsg("\033[32mDIFF:%s\033[0m" % str(log))
                    #self.lobby.send_to_all("\033[31mDIFF:%s\033[0m\n\r" % str(log))
                else:
                    log = " + %s" % i
                    #pyro.sendmsg("\033[31mDIFF:%s\033[0m" % str(log))
                    #self.lobby.send_to_all("\033[32mDIFF:%s\033[0m\n\r" % str(log))
                #self.loger(log)
                # diff1.append(data1)
        self.redisdb.set(name, '0')
        dt1 = datetime.datetime.now()
        delta = dt1 - dt
        log = "thread <font color=green>%s</font> started at <font color=blue>%s</font>. end time is <font color=red>%s</font>. delta: <font color=#FF00FF>%s</font>" % (
            name, dt, dt1, delta)
        try:
            self.loger(log)
        except:
            sys.stderr.write("%s \n" % log)
        pyro.sendmsg("\033[96mget proxy diff thread. mode: %s stopped.\033[0m" % str(name))
        # for data1 in ddata2 :
        #    if not data1 in ddate2:
        #        diff2.append(data1)
    def apc(self, sock):
        self.lobby.send_to_all("\033[32m%s\033[0m\n\r" % "APC STATUS START")
        global threadLife
        p = mp.current_process()
        try:
            pf = open('/tmp/elis_apc.pid', 'r')
            proxy_pid = int(pf.read().strip())
            os.kill(int(proxy_pid), SIGTERM)
            pf.close()
        except:
            pass
        pf = open('/tmp/elis_apc.pid', 'w')
        pf.write(str(p.pid))
        pf.close()
        setproctitle("elis_rizon: apc status")
        sys.stderr.write("%s started pid=%s \n" % (p.name, p.pid))
        sys.stderr.flush()
        greeting_maker = Pyro4.Proxy(self.uri)
        greeting_maker.proces("add", p.name, p.pid)
        interesting = ('status', 'loadpct', 'bcharge', 'timeleft')
        apc_status = {}   
        #global previus_state
        previus_state = {'status' : '', 'bcharge' : '100.0', 'temp' : 20}
        time.sleep(20)
        state = 100
        check = True
        CoreTemperature = 20
        while check:
            time.sleep(2)
            try:
                res = check_output("/sbin/apcaccess")
                temerature = check_output("/usr/bin/sensors")
                for lm_sensors in temerature.split('\n'):
                    if 'Core 0' in lm_sensors:
                    	CoreTemperature = int(re.compile(r'Core 0:\W+(?P<temp>[\d]{1,3})', re.I).search(
                                lm_sensors).group('temp'))
                msg = ''
                for line in res.split('\n'):
                    (key, spl, val) = line.partition(': ')
                    key = key.rstrip().lower()
                    val = val.strip()
                    apc_status[key] = val.replace(' Percent','%')
                if previus_state['temp'] - CoreTemperature > 0:
                    tempDelta = previus_state['temp'] - CoreTemperature
                else:
                    tempDelta = CoreTemperature - previus_state['temp']
                if tempDelta >= 2:
                    previus_state['temp'] = CoreTemperature
                    self.vk_status('%s. Core temperature %s degrees.' % (apc_status['status'],CoreTemperature)) 
                if apc_status['status'] != previus_state['status'] and apc_status['status'] == "ONLINE" :
                    sock.send("PRIVMSG #trollsquad :UPS Status: 03%s. Core temperature %s degrees.\n\r" % (apc_status['status'],CoreTemperature) )
                    self.vk_message('%s --> UPS Status: %s' % (datetime.datetime.now(),apc_status['status']) )
                    previus_state['status'] = apc_status['status']
                    previus_state['bcharge'] = 100
                    self.vk_status('%s. Core temperature %s degrees.' % (apc_status['status'],CoreTemperature))
                if apc_status['status'] == 'ONBATT':
                    state = int(apc_status['bcharge'].split('.')[0])
                    if apc_status['status'] != previus_state['status'] :
                        self.vk_message('%s --> UPS Status: %s' % (datetime.datetime.now(),apc_status['status']) )
                        sock.send("PRIVMSG #trollsquad :UPS Status: 03%s\n\r" % apc_status['status'] )
                        previus_state['status'] = apc_status['status']
                        self.vk_status('%s. Core temperature %s degrees.' % (apc_status['status'],CoreTemperature))
                    if apc_status['bcharge'] != previus_state['bcharge']:
                        if (int(previus_state['bcharge']) - 10 ) >= state or int(state) <= 32 :
                            previus_state['bcharge'] = apc_status['bcharge'].split('.')[0]
                            sock.send("PRIVMSG #trollsquad :UPS Status: 04%s , Battery charge: 04%s , UPS Load: %s , Time Left: 04%s\n\r" %
                                (apc_status['status'], apc_status['bcharge'], apc_status['loadpct'], apc_status['timeleft']))
                            msg = "UPS Status: %s , Battery charge: %s , UPS Load: %s , Time Left: %s" %\
                                (apc_status['status'], apc_status['bcharge'], apc_status['loadpct'], apc_status['timeleft'])
                            #self.vk_message(msg)
                        
                        if int(state) <= 32:
                            msg = "%s --> UPS Status: %s , Battery charge: %s , UPS Load: %s , Time Left: %s" %\
                                (datetime.datetime.now(),apc_status['status'], apc_status['bcharge'], apc_status['loadpct'], apc_status['timeleft'])
                            self.vk_message(msg)
                            sock.send("PRIVMSG #trollsquad :UPS Status: 04%s , Battery charge: 04%s , UPS Load: %s , Time Left: 04%s\n\r" %
                                (apc_status['status'], apc_status['bcharge'], apc_status['loadpct'], apc_status['timeleft']))
                        if int(state) = 31:
                            self.vk_wallPost('Низкий заряд батареи. До отключения %s' % apc_status['timeleft'] )
                        if int(state) <= 30:
                            self.vk_status('SERVER STATUS: OFFLINE')
                            self.vk_wallPost('Батарея разряжена. Отключаюсь')

                        #msg = "%s --> UPS Status: %s , Battery charge: %s , UPS Load: %s , Time Left: %s" %\
                        #        (datetime.datetime.now(),apc_status['status'], apc_status['bcharge'], apc_status['loadpct'], apc_status['timeleft'])
                        #self.lobby.send_to_all("\033[32m%s\033[0m\n\r" % msg)
                        #msg = "Previus state: \033[32m%s\033[0m Current state: \033[33m%s\033[0m" % (int(previus_state['bcharge']), state)
                        #self.lobby.send_to_all("%s\n\r" % msg)
                    #msg = "%s --> UPS Status: %s , Battery charge: %s , UPS Load: %s , Time Left: %s" %\
                    #            (datetime.datetime.now(),apc_status['status'], apc_status['bcharge'], apc_status['loadpct'], apc_status['timeleft'])
                    #self.lobby.send_to_all("\033[32m%s\033[0m\n\r" % msg)
            except:
                self.lobby.send_to_all("\033[32m%s\033[0m\n\r" % 'Что-то пошло не так')
            finally:
                try:
                    pid = greeting_maker.listProcesses()[p.name]
                # sys.stderr.write("%s -> %s \n" % (pid,p.pid)  )
                # sys.stderr.flush()
                    if int(pid) == int(p.pid):
                        check = True
                    else:
                        check = False
                        sys.stderr.write("%s -> %s \n" % (pid, p.pid))
                        sys.stderr.flush()
                except:
                    setproctitle("elis_rizon: error on sending request. uri = %s" % self.uri)
                    time.sleep(60)
                    check = False
                    time.sleep(30)
    def vk_message(self,text):
        try:
            host = "vk.com"
            vkopener.addheaders = [('User-Agent', "Mozilla/5.0 (X11; Linux x86_64; rv:36.0) Gecko/20100101 Firefox/36.0"),
                                   ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                                   ('Accept-Language', 'en-US,en;q=0.5'),
                                   ('Connection', 'keep-alive'),
                                   ('host', host)]
            url = 'https://api.vk.com/method/messages.send'
            formdata = {'user_id': self.user_id, 'message': text, 'access_token': self.token} 
            data_encoded = urllib.urlencode(formdata)
            res = vkopener.open(url, data_encoded)
        except: pass

    def vk_status(self,text):
        try:
            host = "vk.com"
            vkopener.addheaders = [('User-Agent', "Mozilla/5.0 (X11; Linux x86_64; rv:36.0) Gecko/20100101 Firefox/36.0"),
                                   ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                                   ('Accept-Language', 'en-US,en;q=0.5'),
                                   ('Connection', 'keep-alive'),
                                   ('host', host)]
            url = 'https://api.vk.com/method/status.set'
            formdata = {'text': text, 'access_token': self.token} 
            data_encoded = urllib.urlencode(formdata)
            res = vkopener.open(url, data_encoded)
            #self.lobby.send_to_all("\033[32m%s\033[0m\n\r" % res.read())
        except: pass

    def vk_wallPost(self,text):
        try:
            host = "vk.com"
            vkopener.addheaders = [('User-Agent', "Mozilla/5.0 (X11; Linux x86_64; rv:36.0) Gecko/20100101 Firefox/36.0"),
                                   ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
                                   ('Accept-Language', 'en-US,en;q=0.5'),
                                   ('Connection', 'keep-alive'),
                                   ('host', host)]
            url = 'https://api.vk.com/method/wall.post'
            formdata = {'owner_id': self.user_id,'message': text, 'access_token': self.token} 
            data_encoded = urllib.urlencode(formdata)
            res = vkopener.open(url, data_encoded)
            #self.lobby.send_to_all("\033[32m%s\033[0m\n\r" % res.read())
        except: pass

    def shutdown(self):
        try:
            config = ConfigParser.RawConfigParser()
            config.read('%s/bot.cfg' % path)
            ip = config.get("bot", "remote_ip")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip,username='root')
            stdin, stdout, stderr = ssh.exec_command("shutdown -P now")
        except:
            pass
    def flightradar(self,sock,ping_pid):
        self.lobby.send_to_all("\033[32m%s\033[0m\n\r" % "FLIHT RADAR START")
        proc = mp.current_process()
        setproctitle("elis_rizon: open sky")
        try:
            pf = open('/tmp/elis_opensky.pid', 'r')
            proxy_pid = int(pf.read().strip())
            os.kill(int(proxy_pid), SIGTERM)
            pf.close()
        except:
            pass
        pf = open('/tmp/elis_opensky.pid', 'w')
        pf.write(str(proc.pid))
        pf.close()
        api = OpenSkyApi()
        global threadLife
        fl = True
        ship = {}
        while threadLife:
            try:
                states = api.get_states()
                for s in states.states:
                    shipname = s.callsign.strip().rstrip().encode('utf-8')
                    if s.on_ground and s.origin_country == 'Russian Federation':
                        if not ship.has_key(shipname) and shipname != '' :
                            ship[shipname] = s.on_ground
                            self.lobby.send_to_all("\033[32m%s %s %s '%s'\033[0m\n\r" % (shipname,s.geo_altitude,s.on_ground,s.origin_country))
                            #sock.send("PRIVMSG %s :Информбюро бесполезной информации сообщает, что борт %s находится в аэропорту и готовится к взлёту. Такие дела,ребята.\n\r".decode('utf-8').encode('utf-8') % 
                        	#('#trollsquad',shipname))
                    if ship.has_key(shipname) and not s.on_ground:
                        #mat = open("%s/mat" % path, "r").read().split('\n')
                        #secure_random = random.SystemRandom()
                        #sock.send("PRIVMSG %s :%s\n\r" % ('#trollsquad',secure_random.choice(mat)))
                        self.lobby.send_to_all("\033[32mship:'%s'\non ground:%s\naltitude:%s\ncountry:%s\033[0m\n\r" %
                                               (shipname,s.on_ground,s.geo_altitude,s.origin_country))
                        sock.send("PRIVMSG %s :Информбюро бесполезной информации сообщает, что борт %s взлетел. Его высота составляет %s метров над уровнем моря. Такие дела,ребята.\n\r".decode('utf-8').encode('utf-8') % 
                        	('#trollsquad',shipname,s.baro_altitude))
                        del ship[shipname]
                        time.sleep(10)
                        break
                time.sleep(60)
                if psutil.pid_exists(int(ping_pid)):
                    pass
                else:
                    os.kill(int(proc.pid), SIGTERM)
            except:
                self.lobby.send_to_all("\033[32m%s\033[0m\n\r" % "OpenSkyApi error")
                time.sleep(60)
##Angel|off
if __name__ == "__main__":
    daemon = MyDaemon('/tmp/elis_rizon.pid')
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
