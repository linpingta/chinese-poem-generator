#-*- coding: utf-8 -*-
# vim: set bg=dark noet ts=4 sw=4 fdm=indent :
	
""" Generator of Chinese Poem (宋词)"""
__author__ = 'linpingta'


import os
import sys
reload(sys)
sys.setdefaultencoding('utf8')
try:
	import ConfigParser
except ImportError:
	import configparser as ConfigParser
import logging
import re
import simplejson as json
import jieba
from gensim import models

from title_rhythm import TitleRhythmDict

basepath = os.path.abspath(os.getcwd())


class Generator(object):
	""" Generator of Chinese Poem
	"""
	def __init__(self, conf):
		self._ci_words_file = os.path.join(basepath, conf.get('ci', 'ci_words_file'))
		self._ci_rhythm_file = os.path.join(basepath, conf.get('ci', 'ci_rhythm_file'))
		self._ci_result_file = os.path.join(basepath, conf.get('ci', 'ci_result_file'))
		self._support_titles = conf.get('ci', 'support_titles')
		
		# user input
		self._important_words = []
		self._title = ""
		self._force_data_build = False

		# load from data file
		self._title_pingze_dict = {}
		self._pingze_words_dict = {}
		self._pingze_rhythm_dict = {}
		self._rhythm_word_dict = {}
		self._reverse_rhythm_word_dict = {}
		self._reverse_pingze_word_dict = {}

		# split related data
		self._split_sentences = []
		self._word_model = None

		# word count related
		self._word_count_dict = {}
		self._rhythm_count_dict = {}
		
		# storage of related precalculated data
		self._data_files = [
			"title_pingze_dict", "pingze_words_dict", "pingze_rhythm_dict", "rhythm_word_dict", "reverse_rhythm_word_dict", "word_count_dict", "rhythm_count_dict", "split_sentences"
		]

		# store generated poem
		self._result = ""
		# store error reason if no poem generated
		self._error_info = ""

	@property
	def important_words(self):
		return self._important_words
		
	@property
	def title(self):
		return self._title
	
	@property
	def force_data_build(self):
		return self._force_data_build

	@important_words.setter
	def important_words(self, value):
		self._important_words = value
		
	@title.setter
	def title(self, value):
		self._title = value
		
	@force_data_build.setter
	def force_data_build(self, value):
		self._force_data_build = value

	def _build_title_pingze_dict(self, logger):
		for title, content_rhythm in TitleRhythmDict.iteritems():
			#print title
			#print content_rhythm
			#print re.split(", |. |\*|`", content_rhythm)
			sentences = re.findall(r"[0-9]+", content_rhythm)
			new_sentences = []
			for sentence in sentences:
				new_sentence = ""
				for word in sentence:
					if not int(word):
						new_sentence += "0"
					elif not (int(word) % 2):
						new_sentence += "2"
					else:
						new_sentence += "1"
				new_sentences.append(new_sentence)
			self._title_pingze_dict[title] = new_sentences

	def _build_pingze_rhythm_words_dict(self, logger):
		with open(self._ci_rhythm_file, 'r') as fp_r:
			count = 1
			while 1:
				line = fp_r.readline()
				line = line.strip().decode("utf-8")
				if not line:
					continue
				if line == "END":
					break
				if u"：" in line: # Chinese title part
					#print line
					#print len(line)
					next_line = fp_r.readline().strip().decode("utf-8")
					#print 'next', next_line
					words = []
					[ words.append(word) for word in next_line if word not in ["[", "]"] ]
					rhythm_word = line[-2]
					self._rhythm_word_dict[rhythm_word] = words

					# build reverse dict for count later
					for word in words:
						self._reverse_rhythm_word_dict[word] = rhythm_word

					if u"平" in line: # ping related
						self._pingze_words_dict.setdefault('1', []).extend(words)
						self._pingze_rhythm_dict.setdefault('1', []).append(rhythm_word)
						self._reverse_pingze_word_dict[word] = '1'
					else: # ze related
						self._pingze_words_dict.setdefault('2', []).extend(words)
						self._pingze_rhythm_dict.setdefault('2', []).append(rhythm_word)
						self._reverse_pingze_word_dict[word] = '2'
				count += 1
				#if count > 2:
				#	break

	def _count_general_rhythm_words(self, logger):
		with open(self._ci_words_file, 'r') as fp_r:
			count = 1
			while 1:
				line = fp_r.readline()
				line = line.strip().decode("utf-8")
				if not line:
					continue
				if line == "END":
					break
				if (u"，" not in line) and (u"。" not in line): # only use content part for stats
					continue

				sentences = re.split(u"[，。]", line)
				for sentence in sentences:
					if sentence:
						final_word = sentence[-1]
						#print 'final', final_word
						if final_word not in self._reverse_rhythm_word_dict:
							#print 'not exist', final_word
							continue
						rhythm_word = self._reverse_rhythm_word_dict[final_word]
						#print 'rhythm', rhythm_word
						if final_word not in self._word_count_dict:
							self._word_count_dict[final_word] = 1
						else:
							self._word_count_dict[final_word] += 1
						if rhythm_word not in self._rhythm_count_dict:
							self._rhythm_count_dict[rhythm_word] = 1
						else:
							self._rhythm_count_dict[rhythm_word] += 1
				#print line

				count += 1
				if count > 10:
					break

		#import operator
		#sorted_word_count = sorted(self._word_count_dict.items(), key=operator.itemgetter(1))
		#print sorted_word_count[-1][0]

	def _split_words(self, logger):
		""" split words with jieba"""
		with open(self._ci_words_file, 'r') as fp_r:
			count = 1
			while 1:
				line = fp_r.readline()
				line = line.strip().decode("utf-8")
				if not line:
					continue
				if line == "END":
					break
				if (u"，" not in line) and (u"。" not in line): # only use content part for stats
					continue

				print line
				words = jieba.cut(line)
				words = list(words)
				#print '/ '.join(words)
				self._split_sentences.append(words)
				count += 1
				#if count > 10:
				#	break

	def _build_word2vec(self, logger):
		""" build word2vec for words"""
		if not self._split_words:
			logger.error("no split words, skip")
		else:
			self._word_model = models.Word2Vec(self._split_sentences, min_count=5)
			self._word_model.save(os.path.join("data", "word_model"))
			

	def _init_data_build(self, logger):
		""" generate title, pingze, rhythm, word relationship"""
		# mapping title to ping&ze
		self._build_title_pingze_dict(logger)

		# mapping pingze, rhythm to words
		self._build_pingze_rhythm_words_dict(logger)
		
		# mapping rhythm_end to words, 
		self._count_general_rhythm_words(logger)

		# split words
		self._split_words(logger)

		# build word2vec
		self._build_word2vec(logger)

		# save related data
		for data_file in self._data_files:
			value = getattr(self, "_"+data_file)
			with open(os.path.join("data", data_file), "w") as fp_w:
				json.dump(value, fp_w)

	def _load_data_build(self, logger):
		for data_file in self._data_files:
			with open(os.path.join("data", data_file), "r") as fp_r:
				value = json.load(fp_r)
				setattr(self, "_"+data_file, value)
		self._word_model = models.Word2Vec.load(os.path.join("data", "word_model"))

	def _get_format_with_title(self, title, logger):
		if title not in self._title_pingze_dict:
			return -1
		return self._title_pingze_dict[title]

	def _combine_important_word_with_sentence(self, important_words, format_sentences, logger):
		""" 
		make every sentence has one related importance word
		promise pingze order and position order

		we try to use whole word to find similar words first,
		if not, then use each word to find
		"""
		sentence_length = len(format_sentences)

		whole_similar_words = []
		try:
			# treat important words as whole first
			whole_similar_words = self._word_model.most_similar(positive=important_words, topn=2*sentence_length)
		except KeyError as e:
			# treat important word seperately
			whole_similar_words = []
			for important_word in important_words:
				try:
					similar_words = self._word_model.most_similar(positive=[ important_word ], topn=2*sentence_length)
				except KeyError as e1:
					pass
				else:
					for (similar_word, similarity) in similar_words:
						print similar_word, similarity

		# Oops, we don't know what user want, create one randomly
		if not whole_similar_words:
			pass

		# at now, we promise whole_similar_words have enough data
		# now, combine them with sentences
			
		#return [ similar_word for idx, (similar_word, similarity) in enumerate(similar_words) if idx < sentence_length]

	def init(self, logger):
		
		if self._force_data_build:
			self._init_data_build(logger)
		else:
			try:
				self._load_data_build(logger)
			except Exception as e:
				print e
				self._init_data_build(logger)
	
	def check(self, input_param_dict, logger):
		if ('title' in input_param_dict) and (input_param_dict['title'] not in self._support_titles):
			return "%s not defined in support_titles" % input_param_dict['title']

	def generate(self, logger):
		""" main function for poem generated"""

		# get title related sentences
		format_sentences = self._get_format_with_title(self._title, logger)
		if format_sentences < 0:
			raise ValueError("title[%s] not defined in dict" % self._title)

		# combine important words with format sentence
		sentence_word_list = self._combine_important_word_with_sentence(self._important_words, format_sentences, logger)

		# decide rhythm and related words
		pass
	
	def save(self, logger):
		result_info = ""
		if self._result:
			logger.info("save poem to file：%s" % self._result)
			result_info = self._result
		elif self._error_info:
			logger.warning("error info: %s" % self._error_info)
			result_info = self._error_info
		else:
			logger.error("no result output, and no erro info...")
			result_info = u"Oops, no poem generated"
		with open(self._ci_result_file, 'w') as fp_w:
			fp_w.write(result_info)
	
			
if __name__ == '__main__':
	confpath = os.path.join(basepath, 'conf/poem.conf')
	conf = ConfigParser.RawConfigParser()
	conf.read(confpath)
	logging.basicConfig(filename=os.path.join(basepath, 'logs/chinese_poem.log'), level=logging.DEBUG,
		format = '[%(filename)s:%(lineno)s - %(funcName)s %(asctime)s;%(levelname)s] %(message)s',
		datefmt = '%a, %d %b %Y %H:%M:%S'
	)
	logger = logging.getLogger('ChinesePoem')
 
	generator = Generator(conf)
	try:
		# As user input, for theme of poem, and title
		#user_input_dict = dict(title=u"浣溪沙", important_words=[u"菊花", u"庭院"], force_data_build=False)
		user_input_dict = dict(title=u"浣溪沙", important_words=[u"菊花", u"院子"], force_data_build=False)
		#user_input_dict = dict(title=u"浣溪沙", important_words=[u"菊", u"院子"], force_data_build=False)
		print user_input_dict["title"]

		# Init
		generator.force_data_build = user_input_dict["force_data_build"]
		generator.init(logger)
		
		# Generate poem
		error_info = generator.check(user_input_dict, logger)
		if not error_info:
			generator.important_words = user_input_dict["important_words"]
			generator.title = user_input_dict["title"]
		
			logger.info("generate poem for title %s, with important words %s" % (generator.title, str(generator.important_words)))
			generator.generate(logger)
		else:
			generator.error_info = error_info
		   
	except ValueError as e:
		logger.exception(e)
		print e
	except Exception as e:
		logger.exception(e)
		print e
	finally:
		# Save(and tell other) no matter success or not
		generator.save(logger)

