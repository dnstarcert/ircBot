#
# -*- coding: utf-8 -*- 
#
# X-Chat Audacious for Audacious 1.4 and later
# This uses the native Audacious D-Bus interface.
#
# To consider later:
#   - support org.freedesktop.MediaPlayer (MPRIS)?
#
# This script is in the public domain.
#   $Id: xchat-audacious.py 4574 2007-05-16 07:46:17Z deitarion $
import chardet

from dbus import Bus, DBusException
import re
# connect to DBus
bus = Bus(Bus.TYPE_SESSION)
def get_aud():
    try:
        return bus.get_object('org.atheme.audacious', '/org/atheme/audacious')
    except DBusException:
        print "\x02Either Audacious is not running or you have something wrong with your D-Bus setup."
        return None
 
def command_np():
    aud = get_aud()
    audr = bus.get_object('org.mpris.audacious', '/')
    audi = bus.get_object('org.mpris.audacious', '/Player')
    audm = audi.GetMetadata()
    if aud:
 
        pos = aud.Position()
        playLength = aud.Length()
        length = aud.SongLength(pos)
        tlength = (length > 0) and ("%d:%02d" % (length / 60, length % 60)) or "stream"
	if tlength == 'stream':
		np = "say np: " + " - 10[ " + unicode(audm['artist']).encode('utf-8') + " ]10" + " - " + unicode(audm['title']).encode('utf-8') 
		return np
        playSecs = aud.Time() / 1000
        n = playSecs * 11 / length
        info = aud.Info()
        try:
         chars = chardet.detect(unicode(audm['artist']).encode('cp1251'))
        except:
         print "unknown"
         return None
	charsw = chars['encoding'].replace('windows-1251','utf8')
	charsw = charsw.replace('utf-8','cp1251')
	charsw = charsw.replace('utf8','utf-8')
	charsw = charsw.replace('ascii','utf-8')
	#print (unicode(audm).encode('utf-8'))
	#print "Encoding : " + unicode(charsw).encode('utf-8')
	#" - 10[ " + unicode(audm['genre']).encode(charsw) + " ]10" +
        np = "np: " + unicode(audm['artist']).encode(charsw) +  \
" - " + unicode(audm['title']).encode(charsw) + " { " + ("%d:%02d" % (playSecs / 60, playSecs % 60)) + "/" + tlength + " }" +  " { " + str(info[0]/1000) +\
 " kbps" + " / " + str(info[1]/1000) + " kHz } "
    return np,charsw
 


    
