#!/usr/bin/python
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
    # audr = bus.get_object('org.mpris.audacious', '/')
    audi = bus.get_object('org.mpris.audacious', '/Player')
    audm = audi.GetMetadata()
    if aud:
        pos = aud.Position()
        length = aud.SongLength(pos)
        if length <= 0:
            print "possible stream"
            return "", "" 
        cur_pos = aud.Time() / 1000
        info = aud.Info()
        try:
            chars = chardet.detect(unicode(audm['artist']).encode('utf-8'))
            charsw = chars['encoding'].replace('ascii','utf-8')
        except:
            print "unknown"
            return "", ""
        np = "np: %s - %s { %d:%02d/%d:%02d } { %d kbps / %d kHz }"  \
             % (unicode(audm['artist']).encode(charsw),
                unicode(audm['title']).encode(charsw),
                cur_pos / 60, cur_pos % 60,
                length / 60, length % 60, 
                info[0]/1000, info[1]/1000)
        return np, charsw

if __name__ == '__main__':
    command_np() 