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

basepath = os.path.abspath(os.getcwd())


class Generator(object):
    """ Generator of Chinese Poem
    """
    def __init__(self, conf):
        self._ci_words_file = os.path.join(basepath, conf.get('ci', 'ci_words_file'))
        self._ci_rhythm_file = os.path.join(basepath, conf.get('ci', 'ci_rhythm_file'))
        self._ci_result_file = os.path.join(basepath, conf.get('ci', 'ci_result_file'))
        self._support_titles = conf.get('ci', 'support_titles')
        
        self._important_words = []
        self._title = ""
        
        self._result = ""
        self._error_info = ""

    @property
    def important_words(self):
        return self._important_words
        
    @property
    def title(self):
        return self._title
    
    @important_words.setter
    def important_words(self, value):
        self._important_words = value
        
    @title.setter
    def title(self, value):
        self._title = value
        
    def _build_pingze_rhythm_words_dict(self, logger):
	pass

    def _count_general_rhythm_words(self, logger):
	pass

    def init(self, logger):
        
        # mapping rhythm to words, ping&ze : words
        self._build_pingze_rhythm_words_dict(logger)
        
        # mapping rhythm_end to words, 
	self._count_general_rhythm_words(logger)
    
    def check(self, input_param_dict, logger):
        if ('title' in input_param_dict) and (input_param_dict['title'] not in self._support_titles):
            return "%s not defined in support_titles" % input_param_dict['title']

    def generate(self, logger):
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
        # Init
        generator.init(logger)
        
        # As user input, for theme of poem, and title
        user_input_dict = dict(title=u"浣溪沙", important_words=[])
	print user_input_dict["title"]

        # Generate poem
        error_info = generator.check(user_input_dict, logger)
        if not error_info:
            generator.important_words = user_input_dict["important_words"]
            generator.title = user_input_dict["title"]
        
            logger.info("generate poem for title %s, with important words %s" % (generator.title, str(generator.important_words)))
            generator.generate(logger)
        else:
            generator.error_info = error_info
           
    except Exception as e:
        logger.exception(e)
        print e
    finally:
        # Save(and tell other) no matter success or not
        generator.save(logger)

