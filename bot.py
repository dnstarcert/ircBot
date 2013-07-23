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
from chardet.universaldetector import UniversalDetector
import Queue
import urllib2, base64
from PIL import Image
from urlparse import urlparse

from PyQt4 import QtGui
from PyQt4 import QtCore
from np import *
import ConfigParser

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
os.chdir(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))

reviewEdit = {}

CHANNEL_RE = re.compile('PRIVMSG (#?[\w\-]+) :')
NICK_RE = re.compile(":([\w\-]+)!")
IMAGE_RE = re.compile(r"((ht|f)tps?:\/\/[\w\.-]+\/[\w\.-\/]+\.(jpg|png|gif|bmp))")

class MyThread(QtCore.QThread):
   ch = ""
   def __init__(self, parent=None):
    QtCore.QThread.__init__(self, parent)
   def run(self):
   	#print self.ch
   	self.emit(QtCore.SIGNAL("mysignal(QString)"),self.ch)


class MessageBox(QtGui.QMainWindow):
   

   def __init__(self, parent=None,defaultNick="",defaultServer="",defaultPort="",channels=[],defaultEncoding="cp1251"):

        self.defaultNick = defaultNick
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
        self.textCursor = QtGui.QTextCursor()

        reviewEdit["RAW"] = QtGui.QTextEdit()
        reviewEdit["RAW"].setTextInteractionFlags( QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse | QtCore.Qt.LinksAccessibleByKeyboard  )
        print reviewEdit["RAW"].isReadOnly()
        reviewEdit["RAW"].setTextCursor(self.textCursor)
        
        self.tab.addTab(reviewEdit["RAW"],u"RAW")

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
        self.connect(self.buttonNp, QtCore.SIGNAL('clicked()'), self.NowPlay)
        self.connect(self.thread, QtCore.SIGNAL("mysignal(QString)"),self.create_rewed, QtCore.Qt.QueuedConnection)
        self.connect(self.tab, QtCore.SIGNAL('currentChanged(int)'), self.tabChange)

        self.threadLife = 1

   def connectToServer(self):
        self.threadLife = 1
        HOST = self.serverAddr.text()                      
        PORT = int(self.serverPort.text()) 
        myNick = "NICK %s\n\r" % self.nick.text()                
        reviewEdit["RAW"].append("connecting to server %s %s" % (HOST,PORT))
        sock.connect((HOST, PORT))
        sock.send('PONG LAG123124124 \n\r')
        sock.send('USER Ghost 95 * :Phantom \n\r')
        sock.send(myNick)
        t = threading.Thread(target=self.recv_data, args=())
        t.daemon = True
        t.setName("Read data")
        t.start()
        if t.isDaemon() : 
            print "Daemon started"

   def DisconnectFromServer(self):
           sock.send("QUIT :Going to hell\n\r")
           time.sleep(1)
           reviewEdit["RAW"].append("Disconnecting")
           self.threadLife = 0         
           sock.close()
   def sendMessage(self):
        myText = "%s" % self.sendText.text()
        ch = str(self.tab.tabText(self.tab.currentIndex())).encode("cp1251")
        if re.search(r"/me",myText): 
            myText = "PRIVMSG %s :ACTION %s" % (ch,self.sendText.text())
            reviewEdit[ch].append(u"%s> %s" % ("My",myText.replace("/me","")))
            sock.send("%s\n\r" % (myText.encode("cp1251").replace("/me","")))
        elif re.search(r"\ANICK ",myText):
            self.nick.setText(myText[5:])
            sock.send("%s\n\r" % (myText.encode("cp1251")))
            reviewEdit[ch].append(u"%s> %s" % ("My",myText))
        elif re.search(r"\A/join ",myText):
            if not reviewEdit.has_key(myText[6:]) :
             reviewEdit[myText[6:]] = QtGui.QTextEdit()
             reviewEdit[myText[6:]].setReadOnly(True)
             reviewEdit[myText[6:]].setTextCursor(self.textCursor)
             self.tab.addTab(reviewEdit[myText[6:]], myText[6:])
             sock.send("%s\n\r" % (myText[1:].encode(self.defaultEncoding)))
            
        elif re.search(r"\A/part ",myText):
         if reviewEdit.has_key(myText[6:]) :
          self.tab.removeTab(self.tab.indexOf(reviewEdit[myText[6:]]))
          del reviewEdit[myText[6:]]
          sock.send("%s\n\r" % (myText[1:].encode(self.defaultEncoding)))
        elif ch == "RAW": #NOT WORK
          sock.send("%s\n\r" % (myText.encode(self.defaultEncoding)))
          reviewEdit[ch].append(u"%s> %s" % ("My",myText))
        elif ch != "RAW":
          sock.send("PRIVMSG %s :%s\n\r" % (ch,myText.encode(self.defaultEncoding)))
          reviewEdit[ch].append("<font color=red>[%s]</font> <font color=blue>%s </font>:<font color=gray>%s</font>" % (time.strftime("%H:%M:%S"),self.nick.text(),myText))
        self.sendText.setText("")



   def recv_data(self):
        resData = ""
        while self.threadLife:
            try:
                recv_data = sock.recv(4096)
            except:
#Handle the case when server process terminates
                reviewEdit["RAW"].append("Server closed connection, thread exiting.")
                self.threadLife = 0
                #thread.interrupt_main()
                break
            if not recv_data:
  # Recv with no data, server closed connection
                reviewEdit["RAW"].append("Server closed connection, thread exiting2.")
                self.threadLife = 0
                #thread.interrupt_main()
                sock.close()
                break
            else:
                tt = threading.Thread(target=self.worker, args=(recv_data,))
                tt.daemon = True
                tt.setName("Data process")
                tt.start()

   def worker(self,txt):
                if re.search(r"\APING :",txt):
                    #print "Received ping: ", recv_data[:-2]
                    sock.send(u"%s\n\r" % (txt.replace("PING","PONG")))
                elif txt[-5:-2] == ("+iw"):
                    self.onStart = False
                    print "JOIN: "
                    charset = self.DetectEncoding(txt)
                    for x in txt.split("\r\n") :
                        if x != "" :
                            reviewEdit["RAW"].append("<font color=red>[%s] </font>%s" % (time.strftime("%H:%M:%S"),x.decode(charset)))

                    for x in self.channels:
                        setattr(self.thread,"ch",x)
                        self.thread.start()
                        time.sleep(1)
                    reviewEdit["RAW"].append("Connected")
                    tt = threading.Thread(target=self.send_ping, args=())
                    tt.daemon = True
                    tt.setName("ping")
                    tt.start()

                elif re.search(r"JOIN :",txt): pass
                    #sock.send("PRIVMSG %s :VERSION\n\r" % self.UserNick(recv_data))
                elif re.search(r":VERSION ",txt):
                    indx = txt.rfind("VERSION")
                    print indx
                    print recv_data[indx:-3]
                    reviewEdit["RAW"].append("<font color=red>>>></font>%s :%s" % (self.UserNick(txt),txt[indx:-3].decode("cp1251")))
                elif re.search(r" KICK #",txt):
                    p = re.compile(r"( [a-zA-Z0-9].*) :")
                    txt2 = p.findall(txt)[0]
                    indx = txt2.rfind("#")
                    indx2 = txt2[indx:].rfind(" ")
                    indx3 = txt.rfind(":")
                    reason = txt[indx3+1:]
                    ch = txt2[indx:indx+indx2]
                    us_nick = txt2[indx+indx2+1:]
                    if us_nick == self.nick.text():
                       self.tab.removeTab(self.tab.indexOf(reviewEdit[ch]))
                       del reviewEdit[ch]
                       reviewEdit["RAW"].append("<font color=red>[%s] Your kicked from %s. Reason:%s</font>" % (time.strftime("%H:%M:%S"),ch,reason))
                elif re.search(r"VERSION",txt):
                    #reviewEdit.append(repr(recv_data.decode("cp1251")))
                    sock.send("NOTICE %s :VERSION Simple bot writen on python 0.3\n\r" % self.UserNick(txt))
                elif re.search(r"NICK",txt):
                    if self.UserNick == self.nick.text():
                        indx = txt.rfind("NICK") + 6
                        self.nick.setText(txt[indx:])
                        reviewEdit["RAW"].append("<font color=red>[%s] </font><font color=orange>Your nick is %s now</font>" % (time.strftime("%H:%M:%S"),txt[indx:]))

                elif re.search(r"PONG",txt): pass

                elif re.search(r"PRIVMSG",txt):
                    tt = threading.Thread(target=self.privmsg, args=(txt,))
                    tt.daemon = True
                    tt.setName("privmsg")
                    tt.start()
                
                elif re.search(r"NOTICE",txt):
                    for x in txt.split("\r\n") :
                        if x != "" :
                            charset = self.DetectEncoding(txt)
                            ch = "RAW"
                            
                            if not self.onStart : 
                                nck = self.UserNick(x)
                                ch = re.compile('NOTICE (#?[\w\-]+) :').search(x).group(1)
                                indx = x.find("NOTICE") + len(ch) + 7
                            else : 
                                nck = ""
                                indx = 0 #x.find(":***")

                            self.changeColor(ch)
                            reviewEdit["RAW"].append("<font color=red>[%s] </font><font color=blue>%s</font> %s<font color=green> (%s)</font>" % (time.strftime("%H:%M:%S"),nck,x[indx:].decode(charset),charset))

                else : 
                    print "Received data: ", txt[:-2].decode(self.defaultEncoding).encode("utf-8")
  
   def privmsg(self,txt):
    ch = self.chan(txt)
    nck = self.UserNick(txt)
    if ch[0] != "#" : 
    	print ch,"--->",nck
    	if not reviewEdit.has_key(nck) : 
            setattr(self.thread,"ch",nck)
            self.thread.start()
            #time.sleep(1)
            
    
    try:
     charset = self.DetectEncoding(txt)    
     print charset
     indx = txt.rfind("PRIVMSG") + len(ch) + 8
     if IMAGE_RE.search(txt): 
        tt = threading.Thread(target=self.link, args=(txt,ch,indx,charset,))
        tt.daemon = False
        tt.setName("image")
        tt.start()
     else : 
        if ch[0] != "#" : 
            ch = nck  
        txt = self.txtReplace(txt)
        self.changeColor(ch)
        reviewEdit[ch].append("<font color=red>[%s] </font><font color=blue>%s</font>%s<font color=green> (%s)</font>" % (time.strftime("%H:%M:%S"),nck,txt[indx:].decode(charset),charset))
     
     if re.search(r"%s" % self.nick.text(),txt): pass
       #sock.send("PRIVMSG %s :what? \n\r" % self.UserNick(txt))
       #sock.send("NOTICE %s :what? \n\r" % self.UserNick(txt))
    except : 
      txt = self.txtReplace(txt)
      reviewEdit["RAW"].append("<font color=red>[%s] </font><font color=purple>%s</font> <font color=blue>%s</font> %s" % (time.strftime("%H:%M:%S"),ch,self.UserNick(txt),txt[indx:]))
      reviewEdit[ch].append("<font color=red>[%s] </font><font color=blue>%s</font>%s<font color=green> (%s)</font>" % (time.strftime("%H:%M:%S"),self.UserNick(txt),txt[indx:].decode(self.defaultEncoding),"error"))
    finally:
      tt = threading.Thread(target=self.loger, args=(txt,ch,indx,))
      tt.daemon = False
      tt.setName("loger")
      tt.start()

   def loger(self,txt,ch,indx):
    f = open("log.html","a")
    txt = self.txtReplace(txt)
    f.writelines("<font color=red>[%s] </font><font color=purple>%s</font> <font color=blue>%s</font>%s<br />" % (time.strftime("%d %m %Y %H:%M:%S"),ch,self.UserNick(txt),txt[indx:]))
    f.close()
   def link(self,txt,ch,indx,charset):
    m = IMAGE_RE.findall(txt)
    for x in xrange(len(m)):
        print "url: %s" % m[x][0]
        res = urllib2.urlopen(m[x][0])
        url = urlparse(m[x][0])
        info = res.info()
        print info.gettype()
        mimetype = info.getmaintype()
        if mimetype == "image" :
            imgSrc = res.read()
            image_64 = base64.encodestring(imgSrc)
            image = "%s;base64,%s" % (info.gettype(),image_64)
            nck = self.UserNick(txt)
            txt = self.txtReplace(txt)
            self.changeColor(ch)
            reviewEdit[ch].append("<img src=\"data:%s\"> <br /><font color=red>[%s] </font><font color=blue>%s</font>%s <font color=green> (%s)</font>" % (image,time.strftime("%H:%M:%S"),nck,txt[indx:].decode(charset),charset))
        else : pass

   def txtReplace(self,txt):
    return cgi.escape(txt)

   def chan(self, line):
    return CHANNEL_RE.search(line).group(1)
# irc.shock-world.com 319

   def UserNick(self, line):
    return NICK_RE.match(line).group(1)   

# CTCP \x01VERSION\x01\                
   def send_ping(self):
    while self.threadLife:
     #qb.textMesgThread.display(len(threading.enumerate()))
     time.sleep(10)
     sock.send("PING :LAG%s\n\r" % time.time())
     
   def DetectEncoding(self,txt):
     chars = txt
     u = UniversalDetector()
     u.feed(chars)
     u.close()
     result = u.result
     if result['encoding']:
       if result['encoding'] == "ISO-8859-2": charset = "cp1251"
       elif result['encoding'] == "ascii": charset = "utf-8"
       elif result['encoding'] == "utf8": charset = "utf-8"
       elif result['encoding'] == "windows-1251": charset = "cp1251"
       elif re.search(r"\AISO-88",result['encoding']): charset = "cp1251"
       elif re.search(r"\Awindows",result['encoding']): charset = "cp1251"
       elif result['encoding'] == "MacCyrillic": charset = "cp1251"
       else : charset = result['encoding']
     return charset
   def whereMe(self):
     time.sleep(30)
     sock.send('WHOIS %s \n\r' % self.nick.text())
   def NowPlay(self):
    try:
        np, charsw = command_np()
        ch = str(self.tab.tabText(self.tab.currentIndex())).encode("cp1251")
        reviewEdit[ch].append("<font color=red>[%s] </font><font color=blue>%s </font>:%s" % (time.strftime("%H:%M:%S"),self.nick.text(),np.decode(charsw)))       
        sock.send("PRIVMSG %s :%s\n\r" % (ch,np.decode(charsw).encode(self.defaultEncoding)))
    except:
        pass
   def create_rewed(self,ch):
    global reviewEdit
    reviewEdit[u"%s" % ch] = QtGui.QTextEdit()
    reviewEdit[u"%s" % ch].setTextInteractionFlags( QtCore.Qt.TextSelectableByMouse | QtCore.Qt.LinksAccessibleByMouse | QtCore.Qt.LinksAccessibleByKeyboard  )
    reviewEdit[u"%s" % ch].setTextCursor(self.textCursor)
    self.tab.addTab(reviewEdit[u"%s" % ch], u"%s" % ch)
    sock.send('JOIN %s \n\r' % ch)
    
   def tabChange(self):
        self.tab.tabBar().setTabTextColor(self.tab.currentIndex(), self.QColorBlack)
   def changeColor(self,ch) :
        if self.tab.indexOf(reviewEdit[ch]) != self.tab.currentIndex() :
                self.tab.tabBar().setTabTextColor(self.tab.indexOf(reviewEdit[ch]), self.QColorRed)

def threadNumber(): 

 items = list() 
 while True:
        itemsCount = len(threading.enumerate())
        qb.textMesgThread.display(itemsCount)
        #print len(items)
        if itemsCount < len(items) : 
            #print "LAGA ",items
            items2 = list(items)
            for xx in threading.enumerate():
             #print xx.getName()
             find1 = qb.model.findItems(xx.getName())
             if len(find1) != 0:
                items2.remove(xx.getName())
            for xx in items2:
                find2 = qb.model.findItems(xx)
                if len(find2) != 0:
                 indx3 = qb.model.indexFromItem(find2[0]).row()
                 qb.model.removeRow(indx3)
                 items.remove(xx)

            #print items2
        for x in threading.enumerate():
          name =  x.getName()
          find = qb.model.findItems(name)
         # print "->%s<-" % len(find)
          if len(find) == 0: 
           #if name == "MainThread":
           item = QtGui.QStandardItem(name)
           qb.model.appendRow(item)
           items.append(name) 
        time.sleep(0.1)

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    config = ConfigParser.RawConfigParser()
    config.read('bot.cfg')
    channels = config.get("bot","channels").split(",")

    qb = MessageBox(None,config.get("bot","nick"),config.get("bot","server"),config.get("bot","port"),channels,config.get("bot","encoding"))
    qb.show()
    reviewEdit["RAW"].append("Bot has been started")
    listener = threading.Thread(target=threadNumber, args=())
    listener.daemon = True
    listener.setName("Thread List")
    listener.start()

    sys.exit(app.exec_())
