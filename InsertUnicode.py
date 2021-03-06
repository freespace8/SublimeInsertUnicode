import sublime, sublime_plugin
import collections, os, urllib2, threading
from os.path import dirname, realpath, basename

BLOCKS = None
NAMES = None

LOAD_PENDING = False

PACKAGE_NAME = "InsertUnicode"
PACKAGE_DIR = dirname(realpath(__file__))

UNICODEDATA_FILENAME = os.path.join(PACKAGE_DIR, 'UnicodeData.txt')
BLOCKS_FILENAME = os.path.join(PACKAGE_DIR, 'Blocks.txt')

UNICODEDATA_URL = 'ftp://ftp.unicode.org/Public/UNIDATA/UnicodeData.txt'
BLOCKS_URL = 'ftp://ftp.unicode.org/Public/UNIDATA/Blocks.txt'

def safe_status_message(s):
	sublime.set_timeout(lambda: sublime.status_message(s), 0)

def readlines_cached(filename, url):
	'''Reads the lines from the given file. If file is not present,
	loads the given URL, saves into the file and returns the lines.
	'''
	try:
		f = open(filename)
		with f:
			return f.readlines()
	except:
		lines = urllib2.urlopen(url).readlines()
		safe_status_message("{0}: got {1}".format(PACKAGE_NAME, basename(filename)))
		with open(filename, 'w') as f:
			f.writelines(lines)
		return lines

def load_data():
	global BLOCKS, NAMES, LOAD_PENDING
	LOAD_PENDING = True
	# This may take some time.
	try:
		blocks = list(read_blocks(readlines_cached(BLOCKS_FILENAME, BLOCKS_URL)))
		names = dict(read_unicodedata_names(readlines_cached(UNICODEDATA_FILENAME,UNICODEDATA_URL)))
		BLOCKS, NAMES = blocks, names
	except Exception, e:
		err = "{0}: Failed to load data".format(PACKAGE_NAME)
		safe_status_message(err)
		print err
		import traceback; traceback.print_exc()
	finally:
		LOAD_PENDING = False



def show_block_list(view, edit):

	names = [b.name for b in BLOCKS]
	def on_done(n):
		if n == -1:
			return
		show_block(view, edit, BLOCKS[n])
	view.window().show_quick_panel(names, on_done, 0)

def show_block(view, edit, block):

	codeunits = xrange(block.min, block.max-1)
	names = [get_label(codeunit, fallback='(unknown)') for codeunit in codeunits]

	def on_done(n):
		if n == -1:
			return
		codeunit = codeunits[n]
		for region in view.sel():
			insertion = my_unichr(codeunit)
			view.insert(edit, region.end(), insertion)

	view.window().show_quick_panel(names, on_done, 0)

def get_label(codeunit, fallback):
	'Returns a pretty label for the given code unit. Uses a fallback name if not found in data'
	name = NAMES.get(codeunit, fallback)
	char = my_unichr(codeunit)
	code = hex(codeunit)
	return u'[{code}] {char} {name}'.format(name=name, char=char, code=code)

def my_unichr(n):
    'unichr() can fail with literals bigger than 0xFFFF (narrow Python build)'
    literal = "u'" + "\U" + hex(n)[2:].rjust(8,'0') + "'"
    return eval(literal)

class InsertUnicodeShowBlockListCommand(sublime_plugin.TextCommand):

	def run(self, edit, **kwargs):
		if BLOCKS is None:
			sublime.status_message('{0}: DB not loaded'.format(PACKAGE_NAME))
			return
		show_block_list(self.view, edit)

class InsertUnicodeShowBlockCommand(sublime_plugin.TextCommand):

	def run(self, edit, **kwargs):
		if BLOCKS is None:
			if LOAD_PENDING:
				sublime.status_message('{0}: Still loading DB'.format(PACKAGE_NAME))
			else:
				sublime.status_message('{0}: DB failed to load'.format(PACKAGE_NAME))
			return
		try:
			name = kwargs.pop('name')
		except:
			raise ValueError("Name not specified")
		try:
			(block,) = (block for block in BLOCKS if block.name.lower() == name.lower())
		except ValueError:
			msg = '{0}: No such block: {1}'.format(PACKAGE_NAME, name)
			sublime.status_message(msg)
			return
		show_block(self.view, edit, block)

UnicodeBlock = collections.namedtuple('UnicodeBlock', 'min max name')

def read_block(line):
	minmax, name = line.split('; ')
	min, max = minmax.split('..')
	min = int(min, 16)
	max = int(max, 16)
	return UnicodeBlock(min=min, max=max, name=name)


def read_blocks(lines):
	for line in lines:
		line = line.strip()
		if not line:
			continue
		if line.startswith('#'):
			continue
		yield read_block(line)

def read_unicodedata_names(lines):
	for line in lines:
		line = line.strip()
		if not line:
			continue
		t = line.split(';')
		code = t[0]
		name = t[1]
		oldname = t[10]
		if name == '<control>':
			name = '<control>: {0}'.format(oldname)
		code = int(code, 16)
		yield (code, name)

def generate_commands():
	'''Generates the set of command defs that you can paste into a sublime-commands file.
	Initially they are commented out, stay safe!
	'''
	command_template = '//\t/* {0:40} */    ,{{"caption": "InsertUnicode: {0}", "command": "insert_unicode_show_block" , "args": {{"name": "{0}"}}}}'
	for b in BLOCKS:
		print command_template.format(b.name)


threading.Thread(target=load_data).start()

#load_data()
#generate_commands()
