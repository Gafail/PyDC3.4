#!/usr/bin/env python
 
# A python port of nmdc
# Also used documentation from http://wiki.gusari.org/index.php?title=Client-to-Hub_handshake
# Warning: hacked together in a few hours
import socket, array
import sys
import threading
 
class PyDC:
    address = '127.0.0.1'
    port = 411
    password = ''
    auto_reconnect = False
    _reconnector = False    #not sure if this is actually needed
    encoding = 'utf8'
    nick = 'pyDC_user'
    desc = 'Update this description!'
    tag = "pyDC 0.1.2"
    share = 0
 
    users = {}
    hubName = ''
 
    connected = False
    debug = False
 
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 
    def onDebug(self, msg):
        if self.debug == True:
            print(msg)
    def onUserJoin(self, user):
        pass
    def onUserPart(self, user):
        pass
    def onUserUpdate(self, user):
        pass
    def onPublic(self, user, msg):
        pass
    def onPrivate(self, user, msg):
        pass
    def onConnect(self):
        pass
    def onDisconnect(self):
        pass
 
 
    def say(self, message):
        self.sock.send(('<' + self.nick + '> ' + self.dc_escape(message) + '|').encode('utf8'))
        
    def pm(self, user, message):
        self.sock.send(('$To: ' + user + ' From: ' + self.nick + ' $<' + self.nick + '> ' + self.dc_escape(message) + '|').encode('utf8'))
 
    def readsock(self):
        buff = ""
        while True:
            
            ###Very temporary Fix ###
            #######################################################
            ###Very temporary Fix ###
            t = self.sock.recv(1)
            
            t = t.decode('utf-8','replace')
            
            ###Very temporary Fix ###
            #######################################################
            ###Very temporary Fix ###
            
            if t != '|':
                buff += t
            else:
                return buff
 
    def connect(self):
        sys.stdout.flush()
        self.sock.connect((self.address, self.port))
        #this.sock.setEncoding(this.opts.encoding)
        self.onDebug('PyDC: Socket opened.')
        while 1:
            self.onDebug('ConnectionTrue')
            t = self.readsock()
            self.onData(t)
            

 
    def disconnect(self):
        self.sock.close()
        self.onDisconnect()
 
    def onError(self):
        print('Connection error');
        if (self.connected):
            self.connected = False; #trigger auto reconnect
            self.sock.close();
            self.onClosed();
 
    def onData(self, data):
        self.onDebug('Received: '+data)
        commands = data.split('|');
 
        for command in commands:
            self.handle(command)
 
    def handle (self, data):
        sys.stdout.flush()
        self.onDebug("Handling: "+data)
        # Short-circuit public chat
        if (data[0] == '<'):
            rpos = data.index('> ')
            user = data[1:rpos]
            msg = data[rpos+2:]
            self.onPublic(user, msg)
            return
        
        if (data[0] == '*'):
            self.onDebug(data)
            return
        
        # Short-circuit system messages
        if (data[0] != '$'):
            self.onDebug(data)
            return
        
        cmd = data.split(' ')[0]
        rem = data[len(cmd) + 1:]
 
        if cmd == '$Lock':
            key = self.lock2key(rem)
            self.sock.send(
                ('$Supports NoGetINFO UserCommand UserIP2|'+
                '$Key '+key+'|'+
                '$ValidateNick '+self.nick+'|').encode()
            )
            return
        
        if cmd == '$Hello':
            if (rem == self.nick):                
                # Handshake
                self.sock.send('$Version 1,0091|'.encode())
                self.sock.send('$GetNickList|'.encode())
                self.sock.send(('$MyINFO '+ self.getmyinfo()+'|').encode())
            else:
                if (rem not in list(self.users.keys())):
                    self.users[rem] = ''
                    self.onUserJoin(rem)
            return
        
        if cmd == '$HubName':
            self.hubName = rem
            return
        
        if cmd == '$ValidateDenide':
            if len(self.password):
                print('Password incorrect.')
            else:
                print('Nick already in use.')
            return
        
        if cmd == '$HubIsFull':
            print('Hub is full.')
            return
        
        if cmd == '$BadPass':
            print('Password incorrect.')
            return
        
        if cmd == '$GetPass':
            self.sock.send(('$MyPass '+self.password+'|').encode(encoding))
            return
        
        if cmd == '$Quit':
            del self.users[rem]
            self.onUserPart(rem)
            return
        
        if cmd == '$MyINFO':
            user = self.parsemyinfo(rem)
            nick = user['nick']
            if nick not in list(self.users.keys()):
                self.users[nick] = ''
                self.onUserJoin(nick)
            self.users[nick] = user
            self.onUserUpdate(user)
            return
        
        if cmd == '$NickList':
            users = rem.split('$$')
            for user in users:
                if len(user) == 0:
                    continue
                if user not in self.users:
                    self.users[user] = ''
                    self.onUserJoin(user)
            return
        
        if cmd == '$To:':
            start = data.index('$<')
            rpos = data.index('> ')
            user = data[start+2:rpos]
            msg = data[rpos+2:]            
            self.onPrivate(user, msg)
            return
        
        if cmd == '$UserIP':
            # Final message in PtokaX connection handshake - trigger connection
            #  callback. This might not always be the case for other hubsofts?
                    
            if (self.connected == False):
                self.onConnect() # Only call once per connection
            self.connected = True
            return
        
        if cmd == '$UserCommand':
            return
            #parts = rem.match(/(\d+) (\d+)\s?([^\$]*)\$?(.*)/)
            #if (parts.length == 5):
            #    this.onUserCommand(+parts[1], +parts[2], parts[3], self.dc_unescape(parts[4]))
        
        # Ignorable:
        if cmd == '$Supports':
            return
        if cmd == '$UserList':
            return
        if cmd == '$OpList':
            return
        if cmd == '$HubTopic':
            return
        
        self.onDebug('Unhandled DC command: "'+cmd+'"')
        raise Exception("Unhandled")
 
    def dc_escape(self, escape_str):
        if len(escape_str) > 0:
            return escape_str.replace('&','&amp;').replace('|','&#124;').replace('$','&#36;')
        else:
            return ' '
 
    def dc_unescape(self, escape_str):
        return (((''+escape_str).replace('&#36;','$')).replace('&#124;','|')).replace('&amp;','&')
 
    def getmyinfo(self):
        myinfostr =  "$ALL " + self.nick + " "
        if len(self.desc) > 0:
            myinfostr += self.desc + " "
        myinfostr += "<"+self.tag+">$ $100  $$"+str(self.share)+"$|"
        return myinfostr
 
    def parsemyinfo(self, myinfostr):
        #$ALL <nick> <description>$ $<connection><flag>$<e-mail>$<sharesize>$
        commands = myinfostr.split('$')
 
        n_d = None
        if '<' in commands[1]:
            i = commands[1].index('<')
            n_d = commands[1][:i].split(' ')
            ret = {
                'nick' : n_d[1],
                'desc' : commands[1][i:-2],
                'tag'  : '',
                'share': commands[-1]
            }
            tpos = ret['desc'].index('<')
            if (tpos != -1):
                ret['tag']  = ret['desc'][tpos+1:]
                ret['desc'] = ret['desc'][:tpos-1]
            return ret
        else:
            n_d = commands[1].split(' ')
            ret = {
                'nick' : n_d[1],
                'desc' : '',
                'tag'  : '',
                'share': commands[-1]
            }
            return ret
    
    def lock2key(self, lock):
        "Generates response to $Lock challenge from Direct Connect Servers"
        lock = [ord(c) for c in lock]
        key = [0]
        for n in range(1,len(lock)):
            key.append(lock[n]^lock[n-1])
        key[0] = lock[0] ^ lock[-1] ^ lock[-2] ^ 5
        for n in range(len(lock)):
            key[n] = ((key[n] << 4) | (key[n] >> 4)) & 255
        result = ""
        for c in key:
            if c in [0, 5, 36, 96, 124, 126]:
                result += "/%%DCN%.3i%%/" % c
            else:
                result += chr(c)
        return result
        
    def locktokey(self, lock):
        "Generates response to $Lock challenge from Direct Connect Servers"
        self.onDebug('Generating $Key from: '+lock)
        lock = array.array('B', [int(i) for i in lock])
        ll = len(lock)
        key = list('0'*ll)
        for n in range(1,ll):
            key[n] = lock[n]^lock[n-1]
        key[0] = lock[0] ^ lock[-1] ^ lock[-2] ^ 5
        for n in range(ll):
            key[n] = ((key[n] << 4) | (key[n] >> 4)) & 255
        result = ""
        for c in key:
            if c in (0, 5, 36, 96, 124, 126):
                result += "/%%DCN%.3i%%/" % c
            else:
                result += chr(c)
        return result
    
    def parseto(self, str):
        #recipient From: sender $<sender> message|
        lpos = str.index('$<')
        rpos = str.index('> ')
        return [ (str[lpos+2: rpos]), (str[rpos+2]) ]

    def _recon():
        pass

    def setautoreconnect(self, enable):
        self.auto_reconnect = enable
        
        if ((enable and self._reconnector) == False):
            pass
        elif ((not enable) and self.reconnetor != False):
            pass
    
    def reconnect(self):
        if (self.sock != None):
            self.disconnect()
        
        self.sock = None