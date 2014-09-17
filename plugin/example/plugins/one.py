metaData 	= { "help": "This is some help", "aliases": ["one", "1"] }

def execute(command, params ):
	for x in params:
		print( x )
	return "testing"
