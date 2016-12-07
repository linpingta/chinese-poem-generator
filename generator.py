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

		self._bigram_word_to_start_dict = {}
		self._bigram_word_to_end_dict = {}
		self._bigram_count_dict = {}
		
		# storage of related precalculated data
		self._data_files = [
			"title_pingze_dict", "pingze_words_dict", "pingze_rhythm_dict", "rhythm_word_dict", "reverse_rhythm_word_dict", "reverse_pingze_word_dict", "word_count_dict", "rhythm_count_dict", "split_sentences", "bigram_word_to_start_dict", "bigram_word_to_end_dict", "bigram_count_dict"
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
			self._title_pingze_dict[title.decode()] = new_sentences

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

					is_ping = True
					if u"平" in line: # ping related
						self._pingze_words_dict.setdefault('1', []).extend(words)
						self._pingze_rhythm_dict.setdefault('1', []).append(rhythm_word)
						is_ping = True
					else: # ze related
						self._pingze_words_dict.setdefault('2', []).extend(words)
						self._pingze_rhythm_dict.setdefault('2', []).append(rhythm_word)
						is_ping = False

					# build reverse dict for count later
					for word in words:
						self._reverse_rhythm_word_dict[word] = rhythm_word

						if is_ping: # ping related
							self._reverse_pingze_word_dict[word] = '1'
						else: # ze related
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

						# build 2-gram
						for idx, word in enumerate(sentence):
							if idx >= len(sentence) - 1:
								break
							first_word = word
							second_word = sentence[idx+1]
							bigram_key = '__'.join([first_word, second_word])
							if bigram_key not in self._bigram_count_dict:
								self._bigram_count_dict[bigram_key] = 1
							else:
								self._bigram_count_dict[bigram_key] += 1
							self._bigram_word_to_start_dict.setdefault(first_word, []).append(bigram_key)
							self._bigram_word_to_end_dict.setdefault(second_word, []).append(bigram_key)

				#print line
				#print 'bigram'
				#print self._bigram_count_dict
				#print self._bigram_word_to_start_dict
				#print self._bigram_word_to_end_dict

				#count += 1
				#if count > 10:
				#	break

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

				#print line
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

		print 'len', len(self._reverse_pingze_word_dict.keys())
		count_ping = 0
		count_ze = 0
		for key, item in self._reverse_pingze_word_dict.iteritems():
			if item == '1':
				count_ping = count_ping + 1
			if item == '2':
				count_ze = count_ze + 1
		print count_ping
		print count_ze
		

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
		is_word_found = False
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

			if len(word_pingze) != len(candidate_word):
				continue

			for j in range(len(positions) - 1): # dont put in rhythm part
				pos_start = positions[j]
				pos_end = positions[j+1]
				tmp_word = format_sentence[pos_start:pos_end] 
				if (len(tmp_word) == len(word_pingze)) and (self._compare_words(tmp_word, word_pingze)):
					# write word here
					for p, m in enumerate(range(pos_start, pos_end)):
						position_word_dict[m] = candidate_word[p]
					is_word_found = True
					break

			if is_word_found:
				break

		# force fill by order
		pass

		print 'positoin_word_dict', position_word_dict
		for key, item in position_word_dict.iteritems():
			print key, item

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
		whole_similar_words = sorted(whole_similar_words, key=itemgetter(1), reverse=True)
		candidate_words = whole_similar_words[:candidate_length]
		logger.info("generate candidate_words[%s] based on important_words[%s]" % (str(candidate_words), str(important_words)))
		#print 'whole', len(whole_similar_words), whole_similar_words
		print 'candidate', len(candidate_words), candidate_words

		# at now, we promise whole_similar_words have enough data
		# now, combine them with sentences
		already_used_words = []
		for format_sentence in format_sentences:
			keyword_sentence = self._combine_candidate_word_with_single_sentence(format_sentence, candidate_words, already_used_words, logger)
			keyword_sentences.append(keyword_sentence)

		return keyword_sentences

	def _generate_common_rhythm(self, is_ping=True):
		""" generate common rhythm"""

		candidate_rhythms = self._pingze_rhythm_dict["1"] if is_ping else self._pingze_rhythm_dict["2"]
		#print 'rhythm_count', self._rhythm_count_dict

		candidate_rhythm_count_dict = {}
		for candidate_rhythm in candidate_rhythms:
			if candidate_rhythm in self._rhythm_count_dict:
				candidate_rhythm_count_dict[candidate_rhythm] = self._rhythm_count_dict[candidate_rhythm]

		candidate_rhythm_count_dict = sorted(candidate_rhythm_count_dict.items(), key=operator.itemgetter(1), reverse=True)
				
		count = 0
		narrow_candidate_rhythms = []
		for (rhythm, rhythm_count) in candidate_rhythm_count_dict:
			narrow_candidate_rhythms.append((rhythm, rhythm_count))
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

		candidate_word_count_dict = {}
		for candidate_word in candidate_words:
			if candidate_word in self._word_count_dict:
				candidate_word_count_dict[candidate_word] = self._word_count_dict[candidate_word]

		candidate_word_count_dict = sorted(candidate_word_count_dict.items(), key=operator.itemgetter(1), reverse=True)
		return candidate_word_count_dict

	def _generate_common_rhythm_words(self, is_ping=True):
		""" generate rhythm words
		first, generate common rhythm
		second, generate words based on rhythm
		"""

		rhythm = self._generate_common_rhythm(is_ping)
		logger.info("use rhythm[%s] for generatoin" % rhythm)
		return self._generate_common_words(rhythm, is_ping)

	def _generate_rhythm(self, format_sentences, word_sentences, logger):
		""" generate rhythm"""

		# generate ping word with count
		ping_word_count_dict = self._generate_common_rhythm_words(True)
		print 'ping', ping_word_count_dict

		# genrate ze word with count
		ze_word_count_dict = self._generate_common_rhythm_words(False)
		print 'ze', ze_word_count_dict

		already_used_rhythm_words = []
		for format_sentence, word_sentence in zip(format_sentences, word_sentences):
			rhythm_word = ""
			if format_sentence[-1] == '1':
				rhythm_word = self._weighted_choice(ping_word_count_dict, already_used_rhythm_words)
			elif format_sentence[-1] == '2':
				rhythm_word = self._weighted_choice(ze_word_count_dict, already_used_rhythm_words)
			elif format_sentence[-1] == '0':
				rhythm_word = self._weighted_choice(ping_word_count_dict + ze_word_count_dict, already_used_rhythm_words)
			else:
				logger.error("rhythm_type[%s] illegal" % format_sentence[-1])
			already_used_rhythm_words.append(rhythm_word)

			word_sentence[len(format_sentence)-1] = rhythm_word
				
	def _fill_word(self, direction, tofill_position, format_sentence, word_sentence, global_repeat_words, logger):
		""" fill word by related word, and position"""

		seed_word = word_sentence[tofill_position - direction]

		# check 2-gram dict

		# check pingze order

		# select and fill
		selected_word = u""
		word_sentence[tofill_position] = selected_word

	def _sub_generate(self, format_sentence, word_sentence, global_repeat_words, logger):
		""" recursion generate"""

		sentence_length = len(format_sentence)

		# all position filled, return
		if len(word_sentence.keys()) == sentence_length:
			return

		# show candidate positions based on current filled positions
		candidate_positions = []
		[ candidate_positions.append(i) for i in range(sentence_length) if ((i-1) in word_sentence) or ((i+1) in word_sentence) ]
		if not candidate_positions:
			raise ValueError("candidation_position len zero")
		if len(candidate_positions) == 1:
			tofill_position = candidate_positions[0]
		else: # random choose one
			idx = random.randint(0, len(candidate_positions))
			tofill_position = candidate_positions[idx]

		up_fill_direction = (tofill_position - 1) in word_sentence
		down_fill_direction = (tofill_position + 1) in word_sentence
		both_fill_direction = up_fill_direction and down_fill_direction

		if both_fill_direction: # consider format, choose only one, consider later
			up_fill_direction = False

		both_fill_direction = up_fill_direction and down_fill_direction
		assert (not both_fill_direction)

		# fill word one by one
		if up_fill_direction:
			self._fill_word(1, tofill_position, format_sentence, word_sentence, global_repeat_words, logger)
		else:
			self._fill_word(-1, tofill_position, format_sentence, word_sentence, global_repeat_words, logger)

	def _generate(self, format_sentences, word_sentences, logger):
		""" generate poem based on important words and rhythm word"""

		# generate each sentence
		global_repeat_words = []
		[ self._sub_generate(format_sentence, word_sentence, global_repeat_words, logger) for (format_sentence, word_sentence) in zip(format_sentences, word_sentences) ]

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
			return "%s not defined in support_titles" % input_param_dict['title']

	def generate(self, logger):
		""" main function for poem generated"""

		# get title related sentences
		format_sentences = self._get_format_with_title(self._title, logger)
		if format_sentences < 0:
			raise ValueError("title[%s] not defined in dict" % self._title)

		# combine important words with format sentences
		word_sentences = self._combine_important_word_with_sentence(self._important_words, format_sentences, logger)

		# decide rhythm and related words
		self._generate_rhythm(format_sentences, word_sentences, logger)
	
		print 'final'
		print format_sentences
		print word_sentences

		# now, generate poem
		self._generate(format_sentences, word_sentences, logger)

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

