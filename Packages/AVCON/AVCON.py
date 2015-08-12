import sublime, sublime_plugin
import os
import threading


SETTINGS = {}

class DecodingCache(object):
	def __init__(self):
		self.max_size = -1
		self.cache = []

	def set_max_size(self, max_size):
		self.max_size = max_size

	def set_cache(self, new_cache):
		self.cache = new_cache

	def get_cache(self):
		return self.cache

def plugin_loaded():
	init_settings()
	setup_views()

def get_settings():
	settings = sublime.load_settings('AVCON.sublime-settings')
	decoding_cache.set_max_size(settings.get('max_cache_size', 100))
	SETTINGS['encode_key'] = settings.get('encode_key', 58)
	SETTINGS['max_detect_words'] = settings.get('max_detect_words', 102400)
	SETTINGS['decoding_on_load'] = settings.get('decoding_on_load', 'always')
	SETTINGS['encoding_on_save'] = settings.get('encoding_on_save', 'always')

def get_setting(view, key):
	# read project specific settings first
	return view.settings().get(key, SETTINGS[key]);

def init_settings():
	global decoding_cache
	decoding_cache = DecodingCache()
	get_settings()
	sublime.load_settings('AVCON.sublime-settings').add_on_change('get_settings', get_settings)

def setup_views():
	# check existing views
	for win in sublime.windows():
		for view in win.views():
			if get_setting(view, 'decoding_on_load') == 'never':
				break
			if view.is_dirty() :
				continue
			decode_file(view)

def decode_file(view):
	file_name = view.file_name()
	if file_name and file_name.endswith('data'):
		cnt = get_setting(view, 'max_detect_words')
		key = get_setting(view, 'encode_key')
		threading.Thread(target=lambda: decode(view, file_name, cnt, key)).start()

# The decode file thread main method
def decode(view, file_name, cnt, key):
	if not file_name or not os.path.exists(file_name):
		return
	sublime.set_timeout(lambda: view.set_status('origin_decoding', 'Decoding, please wait...'), 0)
	fp = open(file_name, 'rb')
	new_cache = bytearray(fp.read())
	for x in range(len(new_cache)):
		new_cache[x] = (~new_cache[x])&0xff
		new_cache[x] ^= key
	fp.close()
	decoding_cache.set_cache(new_cache)
	sublime.set_timeout(lambda: reloadView(view), 0)

# The encode 
def encode(view, file_name, cnt, key):
	if not file_name or not os.path.exists(file_name):
		return
	sublime.set_timeout(lambda: view.set_status('origin_encoding', 'Encoding, please wait...'), 0)
	fp = open(file_name, 'rb')
	new_cache = bytearray(fp.read())
	for x in range(len(new_cache)):
		new_cache[x] ^= key
		new_cache[x] = (~new_cache[x])&0xff
	fp.close()
	decoding_cache.set_cache(new_cache)
	sublime.set_timeout(lambda: reloadView(view), 0)

# Invalidate view, show decoded file
def reloadView(view):
	view.run_command('avcon_reload')

# Command respond
class AvconReloadCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		regions = sublime.Region(0, self.view.size())
		data = bytearray(decoding_cache.get_cache())
		self.view.replace(edit, regions, data.decode('utf-8'))

# EventListener
class AVCONListener(sublime_plugin.EventListener):
	def on_load(self, view):
		decode_file(view)
