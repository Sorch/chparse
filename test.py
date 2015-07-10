import chparse

class Bot(chparse.chParser):

	def onMsg(self, group, user, msg):
		print(group.group + ": " + msg.name + ": " + msg.body)
		post = msg.body
		if post[0] == ".":
			data = post[1:].split(" ", 1)
			if len(data) > 1:
				cmd, args = data[0], data[1]
			else:
				cmd, args = data[0], ""

			if cmd == "say":
				if(len(args)) < 1:
					group.put("I can't say nothing -_-\"")
				else:
					group.put(args)



bot = Bot(["groups", "list"], "botname", "andofcpswd").run()
