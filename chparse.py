################################################################
# File: chparse.py
# Title: A Chatango Library of sorts...
# Author: sorch/theholder <support@sorch.info>
# Version: 0.1b
# Description:
#  An event-based library for connecting to one or multiple Chatango groups
#  With support for banning deleting 
################################################################

################################################################
# License
################################################################
# Copyright 2015 Contributing Authors
# This program is distributed under the terms of the GNU GPL.
#################################################################
import re
import socket
import time
import random
import requests
import threading
import html

_tags = {'specials': {'mitvcanal': 56, 'animeultimacom': 34, 'cricket365live': 21, 'pokemonepisodeorg': 22, 'animelinkz': 20, 'sport24lt': 56, 'narutowire': 10, 'watchanimeonn': 22, 'cricvid-hitcric-': 51, 'narutochatt': 70, 'leeplarp': 27, 'stream2watch3': 56, 'ttvsports': 56, 'ver-anime': 8, 'vipstand': 21, 'eafangames': 56, 'soccerjumbo': 21, 'myfoxdfw': 67, 'kiiiikiii': 21, 'de-livechat': 5, 'rgsmotrisport': 51, 'dbzepisodeorg': 10, 'watch-dragonball': 8, 'peliculas-flv': 69, 'tvanimefreak': 54, 'tvtvanimefreak': 54}, 'weights' : [['5', 75], ['6', 75], ['7', 75], ['8', 75], ['16', 75], ['17', 75], ['18', 75], ['9', 95], ['11', 95], ['12', 95], ['13', 95], ['14', 95], ['15', 95], ['19', 110], ['23', 110], ['24', 110], ['25', 110], ['26', 110], ['28', 104], ['29', 104], ['30', 104], ['31', 104], ['32', 104], ['33', 104], ['35', 101], ['36', 101], ['37', 101], ['38', 101], ['39', 101], ['40', 101], ['41', 101], ['42', 101], ['43', 101], ['44', 101], ['45', 101], ['46', 101], ['47', 101], ['48', 101], ['49', 101], ['50', 101], ['52', 110], ['53', 110], ['55', 110], ['57', 110], ['58', 110], ['59', 110], ['60', 110], ['61', 110], ['62', 110], ['63', 110], ['64', 110], ['65', 110], ['66', 110], ['68', 95], ['71', 116], ['72', 116], ['73', 116], ['74', 116], ['75', 116], ['76', 116], ['77', 116], ['78', 116], ['79', 116], ['80', 116], ['81', 116], ['82', 116], ['83', 116], ['84', 116]]}

def makeServNum(name):
	roomname = name.lower()
	server = _tags['specials'].get(roomname)
	if not server:
		roomname = "q".join(roomname.split("_"))
		roomname = "q".join(roomname.split("-"))
		base36 = int(roomname[0:min(5, len(roomname))], 36)
		r10 = roomname[6:(6 + (min(3, (len(roomname) - 5))))]
		try:
			r7 = int(r10, 36)
		except:
			r7 = 1000
		else:
			if r7 <= 1000: r7 = 1000
		r4 = 0
		r5 = {}
		r6 = sum([x[1] for x in _tags["weights"]])
		for x in range(0, len(_tags["weights"])):
			r4 = r4 + _tags["weights"][x][1] / r6
			r5[_tags["weights"][x][0]] = r4
		for x in range(0, len(_tags["weights"])):
			if ((base36 % r7 / r7) <= r5[_tags["weights"][x][0]]):
				server = _tags["weights"][x][0];
				break
	return int(server)

def AnonID(uid, ts = None):
	uid = str(uid)[4:8]
	aid = ""
	ts = ts or "3452"
	for x in range(0, len(uid)):
		v4 = int(uid[x:x + 1])
		v3 = int(ts[x:x + 1])
		v2 = str(v4 + v3)
		aid += v2[len(v2) - 1:]
	return "!anon" + aid

class InvalidLogin(Exception): pass
class Raiser(Exception): pass

def _parseFont(f):
	"""Parses the contents of a f tag and returns color, face and size."""
	try:
		sizecolor, fontface = f.split("=", 1)
		sizecolor = sizecolor.strip()
		size = int(sizecolor[1:3])
		col = sizecolor[3:6]
		if col == "": col = Non
		face = f.split("\"", 2)[1]
		return col, face, size
	except:
		return None, None, None


def _clean_message(msg):
	n = re.search("<n(.*?)/>", msg)
	if n: n = n.group(1)
	f = re.search("<f(.*?)>", msg)
	if f: f = f.group(1)
	msg = re.sub("<n.*?/>", "", msg)
	msg = re.sub("<f.*?>", "", msg)
	msg = html.unescape(msg)
	p = re.compile(r'<.*?>')
	msg = p.sub('', msg)
	return msg, n, f

class User(object):
	def __init__(self):
		pass

class Group(object):
	def __init__(self, master, group, user = None, passwd = None, gt = "user"):
		self.group = group
		self.master = master
		self.user = user
		self.passwd = passwd
		self.gt = gt
		self.server = "s%d.chatango.com" % (makeServNum(self.group))
		self._firstCommand = True
		self.socket = None
		self.isConn = False
		self._doPing = True
		self.history = []
		self._noid_messages = {}
		self._nameColor = "EE00"
		self._fontColor = "00C3"
		self._fontSize ="10"
		self._fontFace = "0"
		self.users = []
		self._userdata = []
		self.mods = []
		self.banlist = list()


	def connect(self):
		self.pingTimer = threading.Thread(target = self._pushPing)
		self.pingTimer.daemon = True
		self.pingTimer.start()
		try:
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.socket.connect((self.server, 443))
			self.isConn = True
		except socket.error as e:
			self.isConn = False

		if self.user and self.passwd:
			self._pushToGroup("bauth", self.group, self.master.uid, self.user, self.passwd)

	def _recv(self):
		while self.isConn:
			try:
				_buf = b""
				while not _buf.endswith(b"\x00"):
					_buf += self.socket.recv(3024)
			except socket.error:
				pass
			return _buf

	def put(self, contents):
		data = ('<n{nameColor}/><f x{fontSize}{fontColor}="{fontFace}">{contents}'.format(
			nameColor = self._nameColor,
			fontSize = self._fontSize,
			fontColor = self._fontColor,
			fontFace = self._fontFace,
			contents = contents
		))
		self._pushToGroup("bmsg", "t12j", data)


	def die(self):
		self.socket.close()

	def _pushToGroup(self, *args, **kwargs):
		self.send(*args, **kwargs)

	def send(self, *data):
		data = ":".join([str(x) for x in data])
		data = data.encode("utf-8")
		if self._firstCommand:
			data += b"\x00"
			self._firstCommand = False
		else:
			data += b"\r\n\x00"
		self._send(data)


	def _pushPing(self):
		while self._doPing:
			time.sleep(20)
			self._pushToGroup("")

	def _send(self, data):
		if self.isConn:
			try:
				self.socket.send(data)
			except socket.error:
				self.socket.close()
				self.isConn = False


	# Group helper functions
	def Last(self, args, mode = "user"):
		if mode == "user":
			try:
				return [n for n in self.history if n.name.lower() == args.lower()][-1]
			except:
				return False
		if mode == "pid":
			try:
				return [n for n in self.history if n.umid == args][-1]
			except:
				return False

	def delUser(self, args):
		if args:
			if self.Last(args):
				unid  = self.Last(args).umid
				ip = self.Last(args).ip
				if args[0] in ["#","!"]: args = ""
				self._pushToGroup("delallmsg", unid, ip, args)
				return True
			return False


	def delSingleMsg(self, args):
		if args:
			if self.Last(args):
				self._pushToGroup("delmsg", self.Last(args).mid)
				return True
		return False

	def banUser(self, args):
		if args:
			unid  = self.Last(args).umid
			ip = self.Last(args).ip
			if args[0] in ["#","!"]: args = ""
			self._pushToGroup("block", unid, ip, args)
			return True
		return False

	def getLevel(self, args):
		if args in self.mods:
			return 1
		if args == self.owner:
			return 2
		return 0


class Message:
	def __init__(self, **kwargs):
		for kw in kwargs:
			setattr(self, kw, kwargs[kw])


class chParser(object):
	def __init__(self, groups, user = None, passwd = None):
		self.groups = []
		self.user = user
		self.passwd = passwd
		self.uid = str(random.randrange(10 ** 15, (10 ** 16) - 1))
		self.connected = True
		self.threads = {}
		self._i_log = list()

		for group in groups:
			self.makeGroup(Group(self, group, self.user, self.passwd))

	def getroom(self, room):
		try:
			return [n for n in self.groups if n.group == room][-1]
		except:
			return False

	def _addHistory(self, msg, room):
		self.getroom(room).history.append(msg)

	def route(self, group, cmd, args):
		if hasattr(self, "_r_%s" % (cmd)):
			getattr(self, "_r_%s" % (cmd))(group, args)

	def _r_premium(self, group, args):
		args = args[1:]
		if args[0] != "1":
			group._pushToGroup("msgbg", 1)
			self.isPremium = True
		else:
			self.isPremium = False


	def _r_inited(self, group, args):
		group._pushToGroup("g_participants", "start")
		group._pushToGroup("blocklist", "block", "", "next", "500")
		for msg in reversed(self._i_log):
			self._addHistory(msg, group.group)
		#del self._i_log

	def _r_blocked(self, group, args):
		if args[3]:
			group._pushToGroup("blocklist", "block", "", "next", "500")
	
	def _r_unblocked(self, group, args):
		if args[3]:
			group._pushToGroup("blocklist", "block", "", "next", "500")
			for i in group.banlist:
				if i[2] == args[3]:
					group.banlist.remove(i)


	def _r_blocklist(self, group, args):
		if args[1]:
			banlist = ":".join(args[1:]).split(";")
			for b in banlist:
				params = b.split(":")
				group.banlist.append((params[0], params[1], params[2], float(params[3]), params[4]))


	def _r_ok(self, group, args):
		print(">> %s" % group.group)
		group.owner = args[1]
		group.mods = [f.split(",")[0] for f in args[7].split(";")]
		self.ip = args[6]
		group._pushToGroup("getpremium", 1)

	def _r_mods(self, group, args):
		group.mods = args[1:]
		group.mods = [f.split(",")[0] for f in args[1:]]


	def _r_(self, group, args):
		pass

	def _r_n(self, group, args):
		group.usercount =  (int(args[1], 16) or 0)


	def _r_g_participants(self, group, args):
		ul = ":".join(args[1:]).split(";")
		for u in ul:
			u = u.split(":")
			name = self.checkname(u[1], u[2], u[3], u[4])
			group.users.append(name)
			group._userdata.append({"id":u[0],"time":u[1], "uid":u[2], "name":name})

	def _r_participant(self, group, args):
		if len(group.users) == 0:pass
		if hasattr(group._userdata, args[2]):
			olddata = [i for i in group._userdata if i["id"] == args[2]]
			name = self.checkname(args[7], args[3], args[4], args[5])
			if args[1] == "0":# leave
				if olddata[-1]["name"] in group.users:
					group.users.remove(olddata[-1]["name"])
					group._userdata.remove(olddata[-1])
			if args[1] == "1": # join
				if name not in group.users:
					group.users.append(name)
					group._userdata.append({"name":name, "id":args[2], "uid":args[3], "time":args[7]})
			if args[1] == "2": # old switcharoo
				group._userdata.append({"name":name, "id":args[2], "uid":args[3], "time":args[7]})
				if olddata[-1]["name"] in group.users:
					group._userdata.remove(olddata[-1])
					group.users.remove(olddata[-1]["name"])
					group.users.append(name)


	def checkname(self, jtime, uid, name = "None", tname = "None"):
		if name == "None" and tname == "None":
				name = AnonID(uid, jtime)
		elif name == "None":
			name = tname
		else:
			name = name
		return name

	def _r_b(self, group, args):
		args = args[1:]
		posttime, reg_name, tmp_name, uid, umid, index, ip, x = args[:8]
		rawmsg = ":".join(args[9:])
		if reg_name:
			name = reg_name
		elif tmp_name:
			name = "#" + tmp_name
		else:
			name = AnonID(uid, re.search("<n(.*?)/>", rawmsg).group(1))
		post, nColor, fSize = _clean_message(rawmsg)
		nC, f, fS = _parseFont(fSize)
		msg = Message(mtime = posttime, name = name, body = post, raw = rawmsg, uid = uid, umid = umid, index = index, ip = ip, x = x, size = fS, color = nC, face = f)
		group._noid_messages[msg.index] = msg

		group.b = time.time()

		try:
			self.onMsg(group, name, msg)
		except Exception as e:
			print("ERR", e)


	def _r_i(self, group, args):
		args = args[1:]
		posttime, reg_name, tmp_name, uid, umid, index, ip, x = args[:8]
		rawmsg = ":".join(args[9:])
		if reg_name:
			name = reg_name
		elif tmp_name:
			name = "#" + tmp_name
		else:
			name = AnonID(uid, re.search("<n(.*?)/>", rawmsg).group(1))
		post, nColor, fSize = _clean_message(rawmsg)
		nC, f, fS = _parseFont(fSize)
		msg = Message(mtime = posttime, name = name, body = post, raw = rawmsg, uid = uid, umid = umid, index = index, ip = ip, x = x, size = fS, color = nC, face = f)
		del msg.index
		msg.mid = index
		self._addHistory(msg, group.group)
		self._i_log.append(msg)

	def _r_u(self, group, args):
		args = args[1:]
		msg = group._noid_messages.get(args[0])
		if msg:
			group.u = time.time()
			group._noid_messages.pop(msg.index)
			msg.mid = args[1]
			self._addHistory(msg, group.group)


	def _r_delete(self, group, args):
		if len(args) > 1:
			mid = args[1]
		else:
			mid = args[0]
		if mid:
			msg = [f for f in group.history if mid == f.mid]
			if msg:
				msg = msg[0]
				if msg in group.history:
					group.history.remove(msg)


	def _r_clearall(self, group, args):
		for m in group.history:
			group.history.remove(m)

	def _r_deleteall(self, group, args):
		args = args[1:]
		for msgid in args:
			self._r_delete(group, [msgid])


	def _parse(self, group, datas):
		if not datas: return
		datas = datas.split(b"\x00")
		for data in datas:
			data = data.decode("utf-8")
			data = data.split(":")
			self.route(group, data[0].lower().strip(), data)


	def makeGroup(self, group):
		if not group in self.groups:
			self.groups.append(group)



	def makeThread(self, group):
		self.threads[group] = threading.Thread(target = self._run, args = (group,))
		self.threads[group].start()
		return

	def leaveGroup(self, ga):
		gl = []
		for go in self.groups:
			gl.append(go.group)
		if ga in gl:
			group = [f for f in self.groups if f.group.lower() == ga][0]
			self.groups.remove(group)
			group.isConn = False
			group.die()
			del self.threads[group]
			return True
		return False
		

	def joinGroup(self, ga):
		gl = []
		for g in self.groups:
			gl.append(g.group)
		if not ga in gl:
			group = Group(self, ga, self.user, self.passwd)
			self.makeGroup(group)
			self.makeThread(group)
			group._doReconnect = True
			return True
		return False

	def run(self):
		for group in self.groups:
			self.makeThread(group)

	def _run(self, group):
		group.connect()
		try:
			while group.isConn:
				self._parse(group, group._recv())
				time.sleep(0.2)
		except KeyboardInterrupt:
			group.die()



