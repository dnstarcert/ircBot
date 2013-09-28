#!/usr/bin/python
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
import thread
import threading
import sys, inspect, os, tempfile
import cgi
import string, StringIO
import os.path
import time
import re
import ConfigParser
import Queue
import base64,urllib2
from urllib2 import Request, urlopen, URLError
from chardet.universaldetector import UniversalDetector
from PIL import Image
from urlparse import urlparse
from PyQt4 import QtGui, QtCore
from np import *
from cookielib import CookieJar

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
os.chdir(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))

chat_box = {}
cursor = {}


CHANNEL_RE = re.compile('PRIVMSG (#?[\w\-]+) :')
NICK_RE = re.compile(":([\w\-\[\]\|]+)!")
IMAGE_RE = re.compile(r"((ht|f)tps?:\/\/[\w\.-]+\/[\w\.-\/]+\.(jpg|png|gif|bmp))")
HTTP_RE  = re.compile(r"(http:\/\/[^\s]+)")
class MyThread(QtCore.QThread):

    def __init__(self, parent=None):
        QtCore.QThread.__init__(self, parent)

    def run(self):
   	    self.emit(QtCore.SIGNAL("mysignal(QString)"), self.ch)


class MessageBox(QtGui.QMainWindow):
   
    def __init__(self, parent=None, defaultNick="", defaultServer="", 
                defaultPort="", channels=None, defaultEncoding="cp1251"):
        self.defaultNick = defaultNick
        if channels is None:
            self.channels = []
        else:
            self.channels = channels
        self.defaultServer = defaultServer
        self.defaultPort = defaultPort
        self.defaultEncoding = defaultEncoding
        self.QColorRed = QtGui.QColor(255, 0, 0) 
        self.QColorBlack = QtGui.QColor(0, 0, 0) 
        self.onStart = True

        QtGui.QWidget.__init__(self, parent)

        self.setGeometry(100, 100, 800, 210)
        self.setWindowTitle(u'Python bot')
        self.setFixedWidth(1600)
        self.setFixedHeight(810)

#-------interface-----------------------------------------------------------------------
        self.tab = QtGui.QTabWidget(self)
        self.tab.setCurrentIndex(0)
        self.tab.setGeometry(10, 40, 1450, 730)
        self.tab.setTabsClosable(False)
        self.tab.setMovable(True)
        self.tab.setDocumentMode(True)

        self.textMesgTitle = QtGui.QLabel(self)
        self.textMesgTitle.setGeometry(5, 10, 500, 20)
        self.textMesgTitle.setText(u'Адрес сервера:')

        self.textMesgThread = QtGui.QLCDNumber(self)
        self.textMesgThread.setGeometry(540, 10, 50, 20)
        self.textMesgThread.setSegmentStyle(QtGui.QLCDNumber.Flat)

        self.nameMesgThread = QtGui.QListView(self)
        self.nameMesgThread.setGeometry(1470, 40, 120, 730)
        self.model = QtGui.QStandardItemModel(self.nameMesgThread)
        self.item = QtGui.QStandardItem()
        self.nameMesgThread.setModel(self.model)

#-------------------------------------------------------------
        chat_box["RAW"] = QtGui.QTextEdit()
        #cursor["RAW"] = QtGui.QTextCursor(chat_box["RAW"].document())
        #chat_box["RAW"].setTextCursor(cursor["RAW"])
        chat_box["RAW"].setTextInteractionFlags( QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse | QtCore.Qt.LinksAccessibleByKeyboard  )
        # print chat_box["RAW"].isReadOnly()
        self.tab.addTab(chat_box["RAW"],u"RAW")

#-------------------------------------------------------------        
        self.serverAddr = QtGui.QLineEdit(self)
        self.serverAddr.setGeometry(100, 10, 100, 20)
        self.serverAddr.setStatusTip(u'Адрес сервера:')
        self.serverAddr.setText(self.defaultServer)

        self.textMesgTitle = QtGui.QLabel(self)
        self.textMesgTitle.setGeometry(210, 10, 500, 20)
        self.textMesgTitle.setText(u'Порт:')
        
        self.serverPort = QtGui.QLineEdit(self)
        self.serverPort.setGeometry(250, 10, 100, 20)
        self.serverPort.setStatusTip(u'Порт сервера:')
        self.serverPort.setInputMask("90000")
        self.serverPort.setText(self.defaultPort)

        self.textMesgTitle = QtGui.QLabel(self)
        self.textMesgTitle.setGeometry(360, 10, 500, 20)
        self.textMesgTitle.setText(u'Введите ник:')

        self.nick = QtGui.QLineEdit(self)
        self.nick.setGeometry(450, 10, 80, 20)
        self.nick.setStatusTip(u'Ник:')
        self.nick.setText(unicode(self.defaultNick))

        self.sendText = QtGui.QLineEdit(self)
        self.sendText.setGeometry(10, 780, 1450, 20)
        self.sendText.setStatusTip(u'Текст:')

        self.buttonConnect = QtGui.QPushButton(u'Соединиться', self)
        self.buttonConnect.setGeometry(600, 10, 120, 20)
        self.buttonConnect.setShortcut('Ctrl+Enter')
        self.buttonConnect.setStatusTip('Connect')

        self.buttonDisconnect = QtGui.QPushButton(u'Отключиться', self)
        self.buttonDisconnect.setGeometry(730, 10, 120, 20)
        self.buttonDisconnect.setShortcut('Ctrl + Enter')
        self.buttonDisconnect.setStatusTip('Disconnect')

        self.buttonEnc = QtGui.QPushButton(u'Отправить', self)
        self.buttonEnc.setGeometry(1470, 780, 120, 20)
        self.buttonEnc.setShortcut("Return") 
        self.buttonEnc.setStatusTip('Отправить')

        self.buttonNp = QtGui.QPushButton(u'Now playing', self)
        self.buttonNp.setGeometry(1470, 10, 120, 20)
        self.thread = MyThread()


        self.connect(self.buttonConnect, QtCore.SIGNAL('clicked()'), self.connectToServer)
        self.connect(self.buttonDisconnect, QtCore.SIGNAL('clicked()'), self.DisconnectFromServer)
        self.connect(self.buttonEnc, QtCore.SIGNAL('clicked()'), self.sendMessage)
        self.connect(self.buttonNp, QtCore.SIGNAL('clicked()'), self.now_playing)
        self.connect(self.thread, QtCore.SIGNAL("mysignal(QString)"),self.create_rewed, QtCore.Qt.QueuedConnection)
        self.connect(self.tab, QtCore.SIGNAL('currentChanged(int)'), self.tabChange)
        self.connect(chat_box["RAW"], QtCore.SIGNAL('textChanged()'), self.textChanged)

        self.threadLife = 1

    def textChanged(self):
    	global chat_box
        try:
            obj = self.sender()
            cur = obj.textCursor()
            cur.movePosition(13) 
            obj.setTextCursor(cur)
            time.sleep(0.1)
        except : pass



    def connectToServer(self):
        self.threadLife = 1
        HOST = self.serverAddr.text()                      
        PORT = int(self.serverPort.text()) 
        my_nick = "NICK %s\n\r" % self.nick.text()                
        chat_box["RAW"].append("connecting to server %s %s" % (HOST, PORT))
        sock.connect((HOST, PORT))
        sock.send('PONG LAG123124124 \n\r')
        sock.send('USER Ghost 95 * :Phantom \n\r')
        sock.send(my_nick)
        t = threading.Thread(target=self.recv_data, args=())
        t.daemon = True
        t.setName("Read data")
        t.start()

    def DisconnectFromServer(self):
        sock.send("QUIT :Going to hell\n\r")
        time.sleep(1)
        chat_box["RAW"].append("Disconnecting")
        self.threadLife = 0         
        sock.close()

    def sendMessage(self):
        myText = "%s" % self.sendText.text()
        channel = str(self.tab.tabText(self.tab.currentIndex())).encode("cp1251")
        if re.search(r"/me",myText): 
            myText = "PRIVMSG %s :ACTION %s" % (channel, self.sendText.text())
            chat_box[channel].append(u"%s> %s" % ("My", myText.replace("/me", "")))
            sock.send("%s\n\r" % (myText.encode("cp1251").replace("/me", "")))
        elif re.search(r"\ANICK ", myText):
            self.nick.setText(myText[5:])
            sock.send("%s\n\r" % (myText.encode("cp1251")))
            chat_box[channel].append(u"%s> %s" % ("My", myText))
        elif re.search(r"\A/join ", myText):
            if not chat_box.has_key(myText[6:]):
                self.thread.ch = myText[6:]
                self.thread.start()
                #time.sleep(1)
                sock.send("%s\n\r" % (myText[1:].encode(self.defaultEncoding))) 
        elif re.search(r"\A/part ", myText):
            if chat_box.has_key(myText[6:]):
                self.tab.removeTab(self.tab.indexOf(chat_box[myText[6:]]))
                del chat_box[myText[6:]]
                sock.send("%s\n\r" \
                    % (myText[1:].encode(self.defaultEncoding)))
        elif channel == "RAW": #NOT WORK
            sock.send("%s\n\r" % (myText.encode(self.defaultEncoding)))
            chat_box[channel].append(u"%s> %s" % ("My", myText))
        elif channel != "RAW":
            sock.send("PRIVMSG %s :%s\n\r" \
                % (channel, myText.encode(self.defaultEncoding)))
            chat_box[channel].append("<font color=red>[%s]</font> \
                &lt;<font color=blue>%s</font>&gt; <font color=gray>%s</font>" \
                % (time.strftime("%H:%M:%S"), self.nick.text(), myText))
        self.sendText.setText("")

    def recv_data(self):
        while self.threadLife:
            try: 
                recv_data = sock.recv(4096)
            except:
                #Handle the case when server process terminates
                chat_box["RAW"].append("Server closed connection, thread exiting.")
                self.threadLife = 0
                break
            if not recv_data:
                # Recv with no data, server closed connection
                chat_box["RAW"].append("Server closed connection, thread exiting2.")
                self.threadLife = 0
                sock.close()
                break
            else:
                t = threading.Thread(target=self.worker, args=(recv_data,))
                t.daemon = True
                t.setName("Data process")
                t.start()

    def worker(self, text):

        if text.find("PING :") == 0:
            sock.send(u"%s\n\r" % (text.replace("PING", "PONG")))
        elif text.find("Global Users:") > 0 :
            self.onStart = False
            #print "JOIN: "
            charset = self.detect_encoding(text)
            for x in text.split("\r\n"):
                if x:
                    chat_box["RAW"].append("<font color=red>[%s] </font>%s" \
                        % (time.strftime("%H:%M:%S"), x.decode(charset)))

            for x in self.channels:
                self.thread.ch = x.strip()
                self.thread.start()
                time.sleep(1)
            chat_box["RAW"].append("Connected")
            t = threading.Thread(target=self.send_ping, args=())
            t.daemon = True
            t.setName("ping")
            t.start()

        elif "JOIN :" in text: pass
            #sock.send("PRIVMSG %s :VERSION\n\r" % self.get_nick(recv_data))
        elif ":VERSION " in text:
            indx = text.rfind("VERSION")
            print indx
            print recv_data[indx:-3]
            chat_box["RAW"].append("<font color=red>>>></font>&lt;%s&gt; %s" \
                % (self.get_nick(text), text[indx:-3].decode("cp1251")))
        elif " KICK #" in text:
            p = re.compile(r"( [a-zA-Z0-9].*) :")
            text2 = p.findall(text)[0]
            indx = text2.rfind("#")
            indx2 = text2[indx:].rfind(" ")
            indx3 = text.rfind(":")
            reason = text[indx3+1:]
            channel = text2[indx:indx + indx2]
            us_nick = text2[indx+indx2 + 1:]
            if us_nick == self.nick.text():
               self.tab.removeTab(self.tab.indexOf(chat_box[channel]))
               del chat_box[channel]
               chat_box["RAW"].append("<font color=red>[%s] You were \
                kicked from %s. Reason: %s</font>" \
                % (time.strftime("%H:%M:%S"), channel, reason))
        elif "VERSION" in text:
            #chat_box.append(repr(recv_data.decode("cp1251")))
            sock.send("NOTICE %s :VERSION Simple bot writen on python 0.3\n\r" % self.get_nick(text))
        elif "NICK" in text:
            if self.get_nick == self.nick.text():
                indx = text.rfind("NICK") + 6
                self.nick.setText(text[indx:])
                chat_box["RAW"].append("<font color=red>[%s] </font>\
                    <font color=orange>Your nick is %s now</font>" \
                    % (time.strftime("%H:%M:%S") ,text[indx:]))

        elif "PONG" in text: pass

        elif "PRIVMSG" in text:
            t = threading.Thread(target=self.privmsg, args=(text,))
            t.daemon = True
            t.setName("privmsg")
            t.start()
        
        elif "NOTICE" in text:
            for x in text.split("\r\n"):
                if x:
                    charset = self.detect_encoding(text)
                    channel = "RAW"
                    if not self.onStart: 
                        nick = self.get_nick(x)
                        channel = re.compile('NOTICE (#?[\w\-]+) :').search(x).group(1)
                        indx = x.find("NOTICE") + len(channel) + 7
                    else: 
                        nick = ""
                        indx = 0

                    self.changeColor("RAW")
                    chat_box["RAW"].append("<font color=red>[%s] </font>\
                        <font color=blue>%s</font> %s<font color=green> \
                        (%s)</font>" % (time.strftime("%H:%M:%S"), nick,
                            x[indx:].decode(charset), charset))

        else: 
            print ("Received data: ",
                text[:-2].decode(self.defaultEncoding).encode("utf-8"))
  
    def privmsg(self, text):
        channel = self.get_channel(text)
        nick = self.get_nick(text)
        if channel[0] != "#": 
    	    #print channel, "--->", nick
    	    if not chat_box.has_key(nick): 
                self.thread.ch = nick
                self.thread.start()
        try:
            charset = self.detect_encoding(text)    
            #print charset
            indx = text.rfind("PRIVMSG") + len(channel) + 8
            if IMAGE_RE.search(text): 
                t = threading.Thread(target=self.link,
                    args=(text, channel, indx, charset,))
                t.daemon = False
                t.setName("image")
                t.start()
            
            elif HTTP_RE.search(text):
            	t = threading.Thread(target=self.http_title,
                    args=(text, channel,))
                t.daemon = False
                t.setName("http")
                t.start()
            	#self.http_title(text, channel)

            elif channel[0] != "#": 
                    channel = nick  
            text = self.escape_html(text)
            self.changeColor(channel)
            chat_box[channel].append("<font color=red>[%s] </font>\
                &lt;<font color=blue>%s</font>&gt; %s<font color=green> (%s)</font>" \
                % (time.strftime("%H:%M:%S"), nick,
                    text[indx+2:].decode(charset), charset))
            if re.search(r"%s" % self.nick.text(), text): pass
                #sock.send("PRIVMSG %s :what? \n\r" % self.get_nick(text))
                #sock.send("NOTICE %s :what? \n\r" % self.get_nick(text))
        except: 
            text = self.escape_html(text)
            chat_box["RAW"].append("<font color=red>[%s] </font>\
                <font color=purple>%s</font> <font color=blue>%s</font> %s" \
                % (time.strftime("%H:%M:%S"), channel,
                    self.get_nick(text), text[indx:]))
            chat_box[channel].append("<font color=red>[%s] </font>\
                <font color=blue>%s</font>%s<font color=green> (%s)</font>" \
                % (time.strftime("%H:%M:%S"), self.get_nick(text),
                    text[indx:].decode(self.defaultEncoding), "error"))
        finally:
            t = threading.Thread(target=self.loger, args=(text, channel, indx,))
            t.daemon = False
            t.setName("loger")
            t.start()

    def loger(self, text, channel, indx):
        f = open("log.html","a")
        text = self.escape_html(text)
        f.writelines("<font color=red>[%s] </font><font color=purple>%s\
            </font> <font color=blue>%s</font>%s<br />" \
            % (time.strftime("%d %m %Y %H:%M:%S"), channel,
                self.get_nick(text), text[indx:]))
        f.close()

    def link(self, text, channel, indx, charset):
        m = IMAGE_RE.findall(text)

        for x in xrange(len(m)):
            url = m[x][0]
            print "url: %s" % url
            res = urllib2.urlopen(url)
            info = res.info()
            mimetype = info.getmaintype()
            if mimetype == "image":
                img = Image.open(StringIO.StringIO(res.read()))
                if img.size[0] > 1420 : 
                    img.thumbnail((1420,img.size[1]),Image.ANTIALIAS)
                #output = StringIO.StringIO()
                path = tempfile.mkstemp(suffix = url.replace("/","_"), prefix = '%d_' % x)[1]
                img.save(path) 
                print path
                #img.save(output,format=info.getsubtype())
                #contents = output.getvalue()
                #output.close()
                #obj = StringIO.StringIO(img.tostring())
                #image = "%s;base64,%s" % (info.gettype(),
                #    base64.encodestring(contents))
                #print image

                self.changeColor(channel)
                chat_box[channel].append("<a href=\"%s\"><img src=\"%s\" /></a>" % (url, path))
                res.close()
    
    def http_title(self, text, channel):
        #print text
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
                print info
                mimetype = info.getmaintype()
                ext = info.getsubtype()
                if mimetype != "image" and mimetype == "text" :
                    sech = re.compile(r"<title>([\s\w\S\n]*)<\/title>").findall(res.read())
                    self.changeColor(channel)
                    charset = self.detect_encoding(sech[0])
                    text = sech[0].decode(charset).replace("\n","").replace("\r","")
                    color = re.compile(r'([0-9]{1,2})')
                    text = color.sub("",text)
                    if len(text) > 300 : text = text[:300]
                    chat_box[channel].append("<a href=\"%s\">%s</a>" % (url, text))
                    if channel == "#trollsquad" or channel == "#test" : sock.send("PRIVMSG %s :12%s\n\r" \
                % (channel, text.encode("cp1251")))
                    res.close()
                elif mimetype == "image":
                    img = Image.open(StringIO.StringIO(res.read()))
                    if img.size[0] > 1420 : 
                        img.thumbnail((1420,img.size[1]),Image.ANTIALIAS)
                    path = tempfile.mkstemp(suffix = url.replace("/","_"), prefix = '%d_' % x)[1]
                    print path
                    img.save("%s.%s" % (path,ext))
                    self.changeColor(channel)
                    chat_box[channel].append("<a href=\"%s\"><img src=\"%s\" /></a>" % (url, "%s.%s" % (path,ext)))
                    res.close()
            except URLError, e: 
            	if hasattr(e, 'reason'):
                    print 'We failed to reach a server.'
                    print 'Reason: ', e.reason
                    chat_box[channel].append("We failed to reach a server.\nReason: %s " % e.reason)
                elif hasattr(e, 'code'):
                    print 'The server couldn\'t fulfill the request.'
                    print 'Error code: ', e.code
                    chat_box[channel].append("The server couldn\'t fulfill the request.\nError code: %s " % e.code)
                else: chat_box[channel].append("<a href=\"%s\">%s</a>" % (url, "404"))
    
    def escape_html(self, text):
        return cgi.escape(text)

    def get_channel(self, line):
        # line: irc.shock-world.com 319
        return CHANNEL_RE.search(line).group(1)

    def get_nick(self, line):
        return NICK_RE.match(line).group(1)   

    # CTCP \x01VERSION\x01\                
    def send_ping(self):
        while self.threadLife:
            #qb.textMesgThread.display(len(threading.enumerate()))
            time.sleep(10)
            sock.send("PING :LAG%s\n\r" % time.time())
     
    def detect_encoding(self, line):
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

    def where_am_i(self):
        time.sleep(30)
        sock.send('WHOIS %s \n\r' % self.nick.text())

    def now_playing(self):
        try:
            np, charsw = command_np()
            channel = str(self.tab.tabText(self.tab.currentIndex())).encode("cp1251")
            chat_box[channel].append("<font color=red>[%s] </font>\
                &lt;<font color=blue>%s</font>&gt; %s" % (time.strftime("%H:%M:%S"), 
                    self.nick.text(), np.decode(charsw)))       
            sock.send("PRIVMSG %s :%s\n\r" \
                % (channel, np.decode(charsw).encode(self.defaultEncoding)))
        except:
            pass

    def create_rewed(self, channel):
        try :
            global chat_box,cursor
            chat_box[u"%s" % channel] = QtGui.QTextEdit()
            #cursor[u"%s" %   channel] = QtGui.QTextCursor(chat_box[u"%s" % channel].document())
            #chat_box[u"%s" % channel].setTextCursor(cursor[u"%s" % channel])
            chat_box[u"%s" % channel].setTextInteractionFlags( QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse | QtCore.Qt.LinksAccessibleByKeyboard  )
            self.tab.addTab(chat_box[u"%s" % channel], u"%s" % channel)
            self.connect(chat_box[u"%s" % channel], QtCore.SIGNAL('textChanged()'), self.textChanged)
            sock.send('JOIN %s \n\r' % channel)
        except : pass


    def tabChange(self):
        self.tab.tabBar().setTabTextColor(self.tab.currentIndex(), self.QColorBlack)

    def changeColor(self, channel):
        if self.tab.indexOf(chat_box[channel]) != self.tab.currentIndex():
            self.tab.tabBar().setTabTextColor(self.tab.indexOf(chat_box[channel]), self.QColorRed)

def threadNumber(): 
    items = []
    while True:
        itemsCount = len(threading.enumerate())
        qb.textMesgThread.display(itemsCount)
        if itemsCount < len(items):
            items2 = items[:]
            for element in threading.enumerate():
                find1 = qb.model.findItems(element.getName())
                if len(find1) != 0:
                    items2.remove(element.getName())
            for element in items2:
                find2 = qb.model.findItems(element)
                if len(find2) != 0:
                    indx3 = qb.model.indexFromItem(find2[0]).row()
                    qb.model.removeRow(indx3)
                    items.remove(element)
        for x in threading.enumerate():
            name =  x.getName()
            find = qb.model.findItems(name)
            if len(find) == 0: 
                item = QtGui.QStandardItem(name)
                qb.model.appendRow(item)
                items.append(name) 
        time.sleep(0.1)

def main():
    global qb
    app = QtGui.QApplication(sys.argv)
    config = ConfigParser.RawConfigParser()
    config.read('bot.cfg')
    channels = config.get("bot", "channels").split(",")
    qb = MessageBox(None, config.get("bot", "nick"),
                    config.get("bot", "server"),
                    config.get("bot", "port"),
                    channels, config.get("bot", "encoding"))
    qb.show()
    chat_box["RAW"].append("Bot has been started")
    listener = threading.Thread(target=threadNumber, args=())
    listener.daemon = True
    listener.setName("Thread List")
    listener.start()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
