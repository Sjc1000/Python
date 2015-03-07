import socket
import threading
import argparse
import sys
import time

class irc():
	log = []
	const = []
	previous = b''
	loggable = ['001','002','003','004','005','JOIN','332','333','353','366','NOTICE','MODE','NICK']
	connected = 0
	def __init__(self, nickname, server, port):
		'''
		A class that connects from the bouncer to IRC.
		It also sends data to the client if its connected.
		If its not connected it will just log the data.
		'''
		self.user = nickname
		self.irc_host = ''
		
		log_thread = threading.Thread(target=self.prlog)
		log_thread.daemon = True
		log_thread.start()
		
		while True:
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.nickname = nickname
			self.server = server
			self.port = port
			try:
				self.socket.connect((server,port))
			except TimeoutError:
				print('Timeout connecting {} to\r\n\tServer: {}\r\n\tPort: {}'.format(nickname, server, port))
				print('Waiting for 30 seconds and trying again!')
				time.sleep(30)
				continue
			self.irc_send('NICK ' + nickname)
			self.irc_send('USER {} {} {} :Uptone Software'.format(nickname, nickname, nickname))
			users[self.user]['irc'] = self.socket
			self.main()
			time.sleep(30)
	
	def sendtoclient(self, data):
		users[self.user]['client'].send(bytes(data + '\r\n', 'utf-8'))
		return 0
	
	def prlog(self):
		while True:
			if users[self.user]['client'] == None:
				self.connected = 0
			if self.log != [] and users[self.user]['client'] != None:
				self.sendtoclient('NOTICE * :*** Previous log ***')
				for l in self.log:
					users[self.user]['client'].send(bytes(l + '\r\n', 'utf-8'))
				self.log = []
				self.sendtoclient('NOTICE * :*** Log finished ***')
			
			
			if self.connected == 0 and users[self.user]['client'] != None:
				for l in self.const:
					self.sendtoclient(l)
				self.connected = 1
		return 0
	
	def main(self):
		while True:
			recv = self.socket.recv(1024)
			if recv.endswith(b'\r\n'):
				self.handle(self.previous + recv)
				self.previous = b''
			else:
				self.previous = self.previous + recv
	
	def handle(self, data):
		try:
			data = data.decode('utf-8')
		except UnicodeDecodeError:
			return 0
		
		for line in data.split('\r\n'):
			if line == '':
				continue
			split = line.split(' ')
			print( line )
			if split[0] == 'PING':
				self.irc_send('PONG {}'.format(split[1][1:]))
				continue
			if split[1] in self.loggable:
				if users[self.user]['client'] != None:
					self.sendtoclient(line)
				self.const.append(line)
			else:
				self.client_send(line)
			self.irc_host = split[0]
			if hasattr(self, 'on' + split[1]):
				getattr(self, 'on' + split[1])(*[split[0]] + split[2:])
		return 0
	
	def client_send(self, data):
		if users[self.user]['client'] == None:
			self.log.append(data)
		else:
			try:
				users[self.user]['client'].send(bytes(data + '\r\n', 'utf-8'))
			except BrokenPipeError:
				users[self.user]['client'] == None;
				self.log.append(data)
		return 0
	
	def irc_send(self, data):
		self.socket.send(bytes(data + '\r\n', 'utf-8'))
		return 0
	
	def on376(self, host, *params):
		self.irc_send('PRIVMSG Nickserv :Identify {} {}'.format(self.user, users[self.user]['nickserv_auth']))
		return 0
	
	def on396(self, *junk):
		channels = users[self.user]['channels']
		for channel in channels:
			self.irc_send('JOIN {}'.format(channel))
		return 0
	
	
	def on433(self, host, ast, nickname, *params):
		self.nickname = nickname + '_'
		self.irc_send('NICK ' + self.nickname)
		return 0

class client():
	'''
	A class to handle all the data from the clients.
	'''
	def __init__(self, socket, user):
		self.socket = socket
		self.user = user
		self.main()
	
	def main(self):
		global users
		while True:
			recv = self.socket.recv(1024)
			try:
				data = recv.decode('utf-8')
			except UnicodeDecodeError:
				continue
			for line in data.split('\r\n'):
				split = line.split(' ')
				if split[0] == 'QUIT':
					users[self.user]['client'] = None
					print('User: ' + self.user + ' has quit.')
					break
				users[self.user]['irc'].send(bytes(line+'\r\n','utf-8'))
		return -1

class handle():
	'''
	A class to handle the connections, checking for username and password
	'''
	def __init__(self, socket, addr):
		self.socket = socket
		self.address = addr
		self.nickname = None
		self.password = None
		self.main()
	
	def notice(self, data):
		self.socket.send(bytes(':{} NOTICE * :*** {} ***\r\n'.format(host, data), 'utf-8'))
		print('[HC] < ' + data )
		return 0
	
	def main(self):
		while True:
			recv = self.socket.recv(1024)
			for line in recv.split(b'\r\n'):
				line = line.decode('utf-8')
				split = line.split(' ')
				if line == '':
					continue
				if hasattr(self, '_' + split[0]):
					response = getattr(self, '_' + split[0])(*split[1:])
					if response == 1:
						self.notice('\x033Client has been linked to IRC. Enjoy this service :D\x03')
						return 0
					if response == -1:
						self.notice('\x035\x02Closing link.\x02\x03')
						self.socket.shutdown(1)
						return 0
		return -1
	
	def _NICK(self, nickname):
		global users
		self.notice('Nickname: \x02' + nickname + '\x02 recieved.')
		if nickname not in users:
			self.notice('\x035Nickname not registered. Please use one that is.\x03')
			return -1
		self.nickname = nickname
		if self.password != None:
			self.notice('Checking your username and password.')
			if users[nickname]['password'] == self.password:
				self.notice('\x033Your username and password match!\x03')
				users[nickname]['client'] = self.socket
				return 1
			else:
				self.notice('\x035Your password does not match!\x03')
				return -1
		else:
			self.notice('Please send your password!')
		return 0
	
	def _PASS(self, password):
		global users
		self.notice('Password: \x02' + password + '\x02 recieved.')
		if self.nickname != None:
			self.notice('Checking your username and password.')
			if users[self.nickname]['password'] == password:
				self.notice('\x033Your username and password match!\x03')
				users[self.nickname]['client'] = self.socket
				return 1
			else:
				self.notice('\x035Your password does not match!\x03')
				return -1
		self.password = password
		return 0


def accept():
	'''
	A constant loop to handle the incoming connections. It will then pass
	the data to handle class which then checks for usernames and passwords.
	'''
	while True:
		socket, addr = server.accept()
		print('New connection made:\n\tAddress: {}\n\tID: {}'.format(str(addr[0]),str(addr[1])))
		handle_thread = threading.Thread(target=handle, args=(socket, addr))
		handle_thread.daemon = True
		handle_thread.start()

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--port', help='The port for the server to run on.', type=int, required=1)
	arguments = parser.parse_args()
	
	
	host = 'localhost' # server name
	port = arguments.port
	max_connections = 5
	users = {'login_and_ircnickname': {'password': 'pass', 'id': None, 'client': None, 'irc': None, 'server': 'irc.freenode.net', 'port': 6667, 'channels': ['#Sjc_Bot'], 'nickserv_auth': 'nickserv_password_here'}}
	
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Creates the socket.
	
	try:
		server.bind((host, port))
	except OSError:
		print('Server could not be bound to {}'.format(str(port)))
		sys.exit(0)
	else:
		print('Server bound at\n\tHost: {}\n\tPort: {}'.format(host, str(port)))
	server.listen(max_connections)
	print('Server listening for ' + str(max_connections) + ' connections.')
	
	connection_thread = threading.Thread(target=accept)
	connection_thread.daemon = True
	connection_thread.start()
	print('Creating the listening thread.')
	
	print('Creating {} IRC connections.'.format(str(len(users))))
	
	for user in users:
		irc_thread = threading.Thread(target=irc, args=(user, users[user]['server'], users[user]['port']))
		irc_thread.daemon = True
		irc_thread.start()
	
	while True:
		for user in users:
			if users[user]['client'] != None and users[user]['id'] == None:
				print('Client has been linked in!')
				client(users[user]['client'], user)
