import imp
from os import listdir
import time



'''
Class:		Plugin
Author:		Sjc1000
Description:	This is a class to easily load plugins into a python script.
Py Version:	It was built in Python3, i haven't tested it with 2.
Notes:		When specifying the PluginFolder you need to specify the trailing / otherwise it will not work.
Plugin File Example:

-------------------------------------------
metaData 	= {"key": "value"}

def execute(command, params ):
	* do stuff *
	return myValue
-------------------------------------------

'''
class plugin:
	''' __init__
			initiates all the variables.
			Then runs the loadPlugins to load the modules. ( Which also gets run each time you call .run()		
	'''	
	def __init__(self, pluginFolder ):
		self.pluginFolder	= pluginFolder
		self.commands 	= {}
		self.loadPlugins()
	
	''' loadPlugins
		Loads all the plugins into a variable which is classwide.
	'''
	def loadPlugins(self):	
		files 		= listdir(self.pluginFolder)
		
		for x in files:
			if ".py" in x:
				current 		= imp.load_source(x[:-3]+"_plugin", pluginFolder + x )
				self.commands[x[:-3]] 	= current
		return 0	

	''' loadMeta
		Loads the metaData dictionary from the file. MetaName is the key in the metaData dict.
	'''
	def loadMeta(self, fromCommand, metaName ):
		metaData 		= self.commands[fromCommand].metaData
		if metaName in metaData:
			return metaData[metaName]
		else:
			return 0

	''' run
		Runs the command, this also supports the commandName being one of the aliases in the command.
		Returns the return value from the execute function of the module if it finds the right module, if not 0 is returned.
	'''
	def run(self, commandName, *params ):
		self.loadPlugins(self.pluginFolder )
		for z in self.commands:
			if any( commandName == cmd for cmd in self.loadMeta(z, "aliases") ):
				return self.commands[z].execute((commandName, self.commands), params)
		return 0
