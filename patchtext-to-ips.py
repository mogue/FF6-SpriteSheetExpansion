# by mogue
# Patch Text 1.0
# Usage: python patchtext-to-ips.py mypatch.patchtext

from struct import *
import sys, os, ntpath, re, shutil

fullname = ''
filename = ''

if len(sys.argv) > 1:
	fullname = sys.argv[1]
	filename = fullname[:fullname.rfind('.')]

def IPSWriteChunk(chunk, file, offset):
	chunk_size = len(chunk)
	while ( chunk_size ):
		if chunk_size > 0xFFFE:
			chunk_size = 0xFFFE

		# write offset
		file.write( pack( 'B', int(offset / 256 / 256) % 256 ) )
		file.write( pack( 'B', int(offset / 256) % 256 ) )
		file.write( pack( 'B', offset % 256 ) )
	
		# write length
		file.write( pack( '>H', chunk_size ) )

		file.write( chunk[:chunk_size] )

		offset += chunk_size
		chunk = chunk[chunk_size:]
		chunk_size = len( chunk )

################################
#	FORMATING              #
################################

offset = 0
data_offset = 0
data_pointer = 0
data_chunk = ''

def format_print(str):
	token = [ '@@', '$$', '**' ]
	ptr   = [ "{0:X}".format( data_pointer + len(data_chunk) ),
	          "{0:X}".format( len(data_chunk) ),
	          "{0:X}".format( data_pointer + offset + len(data_chunk) ) ]

	for symbol in range(0,len(token)):
		while str.find(token[symbol]) != -1:
			idx = str.find(token[symbol])
			c = 2
			while str[ idx + c: idx + c + 2] == token[symbol]:
				c+=2
			str = str[:idx] + ptr[symbol][-c:].zfill(c) + str[idx+c:]
			ptr[symbol] = ptr[symbol][:-c]
	
	return str


################################
#	MAIN PROCESS           #
################################

if os.path.dirname( fullname ) != '': os.chdir( os.path.dirname( fullname ) )

	    # section  offset  file
txt_stack = [ '',      0,      ntpath.basename( fullname ) ]
txtf = 0
ipsf = open( filename + '.ips', 'w')

# IPS header
ipsf.write( "PATCH" )

# Compile
while len(txt_stack) > 0: # each include pushes the stack
	active_filepath = txt_stack.pop()
	if os.path.dirname( active_filepath ) != '': os.chdir( os.path.dirname( active_filepath ) )
	txtf = open( ntpath.basename( active_filepath ), 'r')
	txtf.seek(txt_stack.pop())
	seek_section = txt_stack.pop()
	active_section = ''
	if txtf.tell() != 0: active_section = seek_section

	while 1: # each line in a file
  		line = txtf.readline()
  		if not line: break

		delimiter = line.find(':')

		if   line[:7] == 'section'     or line[:1] == '?':
			arg = re.sub(r'^section|^\?', '', line[:delimiter])
			arg = re.sub(r'^\s+|\s+$', '', arg) # remove surrounding whitespace
			active_section = arg

		if active_section != seek_section: # Early exit if not matching section
			continue

		if   line[:7] == 'section'     or line[:1] == '?':
			line = line
			# do nothing, section already handled
		elif line[:5] == 'print'       or line[:2] == '>>':
			line = re.sub(r'^print|^\>\>', '', line)
			print format_print( line[1:-1] )
			continue
	
		elif line[:3] == 'log'         or line[:2] == '++':
			arg = re.sub(r'^log|^\+\+', '', line[:delimiter])
			arg = re.sub(r'^\s+|\s+$', '', arg) # remove surrounding whitespace
			logf = open( arg, 'a' )
			logf.write( format_print( line[delimiter+1:] ) )
			logf.close()
			continue

		elif line[:7] == 'execute'     or line[:2] == '$':
			arg = re.sub(r'^execute|^\$', '', line)
			arg = re.sub(r'^\s+|\s+$', '', arg) # remove surrounding whitespace
			os.system( arg )
			continue

	
		elif line[:2] == 'at'          or line[:1] == '@':
			arg = re.sub(r'^at|^@', '', line[:delimiter])
			if (len(data_chunk) > 0):
				IPSWriteChunk(data_chunk, ipsf, data_pointer + data_offset)
				data_chunk = ''
			data_offset = offset
			data_pointer = int( arg, 16 )

		elif line[:6] == 'offset'      or line[:1] == '*':
			arg = re.sub(r'^offset|^\*', '', line[:delimiter])
			offset += int(arg, 16)
	
		elif line[:10] == 'binaryfile' or line[:2] == '!b':
			arg = re.sub(r'^binaryfile|^\!b', '', line[:delimiter])
			arg = re.sub(r'^\s+|\s+$', '', arg) # remove surrounding whitespace
			with open( arg, 'r' ) as binf:
				data_chunk += binf.read()
			binf.close()

        	elif line[:7] == 'include'     or line[:1] == '!':
			arg = re.sub(r'^include|^\!', '', line[:delimiter])
			args = arg.split('?')
			while (len(args)<2): args += [ '' ]
			fpath = re.sub(r'^\s+|\s+$', '', args[0]) # remove surrounding whitespace
			fsect = re.sub(r'^\s+|\s+$', '', args[1]) # remove surrounding whitespace
			txt_stack += [seek_section, txtf.tell(),
						os.getcwd() + '/' + ntpath.basename( active_filepath )] 	# from
			txt_stack += [fsect, 0, fpath] 					# to
			break

		elif line[:6] == 'delete'      or line[:2] == '--':
			arg = re.sub(r'^log|^\-\-', '', line[:delimiter])
			arg = re.sub(r'^\s+|\s+$', '', arg) # remove surrounding whitespace
			if os.path.isfile(arg): os.remove(arg)
		else:
			delimiter = 0

		comment = line.find('#')
		if comment != -1: line = line[:comment] + '\n'			

		# parse hex
		if delimiter != -1: line = line[delimiter:]
		else: line = ''

		data = line.upper()
		data = re.sub(r'[^0123456789ABCDEF]', '', data) # strip all but hex
		while len(data) > 0:
			byte = data[:2]
			data = data[2:]
			data_chunk += chr( int(byte, 16) ) 

	txtf.close()

IPSWriteChunk(data_chunk, ipsf, data_pointer + data_offset); # write the last chunk

# IPS footer
ipsf.write('EOF');

ipsf.close();
txtf.close();


