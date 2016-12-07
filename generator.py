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
import random
import operator

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
			"title_pingze_dict", "pingze_words_dict", "pingze_rhythm_dict", "rhythm_word_dict", "reverse_rhythm_word_dict", "reverse_pingze_word_dict", "word_count_dict", "rhythm_count_dict", "split_sentences"
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
				#count += 1
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

				#count += 1
				#if count > 10:
				#	break

		self._word_count_dict = sorted(self._word_count_dict.items(), key=operator.itemgetter(1), reverse=True)
		self._rhythm_count_dict = sorted(self._rhythm_count_dict.items(), key=operator.itemgetter(1), reverse=True)
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

	def _check_position_by_sentence_length(self, sentence_length, logger):
		if sentence_length == 7:
			return [0,2,4,5]
		elif sentence_length == 6:
			return [0,2,4]
		elif sentence_length == 5:
			return [0,2,4]
		elif sentence_length == 4:
			return [0,2]
		elif sentence_length == 3:
			return [0]
		else:
			return []

	def _weighted_choice(self, choices, already_check_choices=[]):
		total = sum(w for (c, w) in choices)
		r = random.uniform(0, total)
		upto = 0
		for c, w in choices:
			if upto + w >= r:
				if c not in already_check_choices:
					return c
			upto += w

	def _compare_words(self, format_words, input_words):
		for (format_word, input_word) in zip(format_words, input_words):
			if format_word == '0': # no check needed
				continue
			if format_word != input_word:
				return False
		return True

	def _combine_candidate_word_with_single_sentence(self, format_sentence, candidate_words, already_used_words, logger):
		"""
		In each sentence, put one candidate word in it
		with consideration of pingze as well as postion and already used condition
		"""
		position_word_dict = {}

		print 'format_sentence', format_sentence

		# remove already used words
		new_candidate_words = [ word for word in candidate_words if word not in already_used_words ]
		if not new_candidate_words:
			logger.warning("use all words, that shouldnt happen")
			new_candidate_words = candidate_words

		sentence_length = len(format_sentence)
		positions = self._check_position_by_sentence_length(sentence_length, logger)
		if not positions: # don't consider position, alread consider pingze
			logger.info("sentence_length[%d] dont check position, as no defined" % sentence_length)

		print 'positions', positions

		# random fill first
		random_already_check_words = []
		for i in range(5):
			candidate_word = self._weighted_choice(new_candidate_words, random_already_check_words)
			if not candidate_word:
				raise ValueError("candidate_word %s" % candidate_word)
			random_already_check_words.append(candidate_word)

			print 'candidate_word', candidate_word

			# get word pingze
			word_pingze = []
			for candidate_word_elem in candidate_word:
				if candidate_word_elem not in self._reverse_pingze_word_dict:
					break
				word_pingze.append(self._reverse_pingze_word_dict[candidate_word_elem])
			print 'word_pingze', word_pingze
			print len(word_pingze), len(candidate_word)
			continue

			if len(word_pingze) != len(candidate_word):
				continue

			for j in range(len(position) - 1): # dont put in rhythm part
				pos_start = position[j]
				pos_end = position[j+1]
				tmp_word = format_sentence[pos_start:pos_end] 
				if (len(tmp_word) == len(word_pingze)) and (self._compare_words(tmp_word, word_pingze)):
					# write word here
					for p, m in enumerate(range(pos_start, pos_end)):
						position_word_dict[m] = candidate_word[p]

		# force fill by order

		return position_word_dict

	def _combine_important_word_with_sentence(self, important_words, format_sentences, logger):
		""" 
		make every sentence has one related importance word
		promise pingze order and position order

		we try to use whole word to find similar words first,
		if not, then use each word to find
		"""
		keyword_sentences = []

		sentence_length = len(format_sentences)
		candidate_length = 3 * sentence_length

		whole_similar_words = []
		try:
			# treat important words as whole first
			whole_similar_words = self._word_model.most_similar(positive=important_words, topn=candidate_length)
			logger.info("get whole_similar_words[%s] based on important_words[%s] as whole" % (str(whole_similar_words), str(important_words)))
		except KeyError as e:
			# treat important word seperately
			whole_similar_words = []
			for important_word in important_words:
				try:
					similar_words = self._word_model.most_similar(positive=[ important_word ], topn=candidate_length)
				except KeyError as e1:
					pass
				else:
					for (similar_word, similarity) in similar_words:
						print similar_word, similarity
					whole_similar_words.extend(similar_words)
					logger.info("get similar_words[%s] based on important_word[%s] seperately" % (str(similar_words), str(important_word)))

		# Oops, we don't know what user want, create one randomly
		if not whole_similar_words:
			logger.warning("Oops, no similar word generated based on important_word[%s] seperately" % str(important_word))

		# order list of tuple, and fetch the first candidate_length of candidates
		from operator import itemgetter
		whole_similar_words = sorted(whole_similar_words, key=itemgetter(1))
		candidate_words = whole_similar_words[:candidate_length]
		logger.info("generate candidate_words[%s] based on important_words[%s]" % (str(candidate_words), str(important_words)))
		#print 'whole', len(whole_similar_words), whole_similar_words
		print 'candidate', len(candidate_words), candidate_words

		# at now, we promise whole_similar_words have enough data
		# now, combine them with sentences
		already_used_words = []
		for format_sentence in format_sentences:
			#keyword_sentence = self._combine_candidate_word_with_single_sentence(format_sentence, candidate_words, already_used_words, logger)
			# tmp, suppose no keyword filled
			keyword_sentence = {}
			keyword_sentences.append(keyword_sentence)
			break
			
		#return [ similar_word for idx, (similar_word, similarity) in enumerate(similar_words) if idx < sentence_length]
		return (format_sentences, keyword_sentences)

	def _generate_common_rhythm(self, is_ping=True):
		""" generate common rhythm"""
		candidate_rhythms = self._pingze_rhythm_dict["1"] if is_ping else self._pingze_rhythm_dict["2"]
		print 'rhythm_count', self._rhythm_count_dict

		count = 0
		narrow_candidate_rhythms = []
		for (rhythm, rhythm_count) in self._rhythm_word_dict:
			if rhythm in candidate_rhythms:
				narrow_candidate_rhythms.append((rhythm, rhythm_count))
				print 'tmp', rhythm, rhythm_count
				count = count + 1
			if count > 5:
				break
		print 'narrow' , narrow_candidate_rhythms
		selected_rhythm = self._weighted_choice(narrow_candidate_rhythms)
		print 'select', selected_rhythm
		return selected_rhythm

	def _generate_common_words(self, rhythm, is_ping=True):
		""" generate common words"""
		candidate_words = self._rhythm_word_dict[rhythm]
		pass

	def _generate_common_rhythm_words(self, is_ping=True):
		""" generate rhythm words
		first, generate common rhythm
		second, generate words based on rhythm
		"""
		rhythm = self._generate_common_rhythm(is_ping)
		#return self._generate_common_words(rhythm, is_ping)

	def _generate_rhythm(self, format_sentences, word_sentences, logger):
		""" generate rhythm"""

		# generate ping rhythm
		ping_words = self._generate_common_rhythm_words(True)

		# genrate ze rhythm
		ze_words = self._generate_common_rhythm_words(False)

		#for format_sentence in format_sentences:
		#	print format_sentence

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
			print input_param_dict['title']
			print 
			return "%s not defined in support_titles" % input_param_dict['title']

	def generate(self, logger):
		""" main function for poem generated"""

		# get title related sentences
		format_sentences = self._get_format_with_title(self._title, logger)
		if format_sentences < 0:
			raise ValueError("title[%s] not defined in dict" % self._title)

		# combine important words with format sentence
		(format_sentences, word_sentences) = self._combine_important_word_with_sentence(self._important_words, format_sentences, logger)

		# decide rhythm and related words
		self._generate_rhythm(format_sentences, word_sentences, logger)
	
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
		user_input_dict = dict(title=u"浣溪沙", important_words=[u"菊花", u"院子"], force_data_build=True)
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

