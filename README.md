# 作诗机 ChinesePoemGenerator
根据用户输入的关键字，生成宋词
这是公司黑客马拉松的一个项目，此处代码文件和[chinese-poem-generator](https://github.com/imagetellerD/chinese-poem-generator)基本一致，是因为后者也是我开发的，但比赛要求建立在公共账户内，所以不得不重复了两个项目，后续更新会以此为主。

[![GitHub stars](https://img.shields.io/github/stars/linpingta/chinese-poem-generator.svg?style=social&label=Star)](https://github.com/linpingta/chinese-poem-generator/stargazers)
[![Fork](https://img.shields.io/badge/-Fork-green?logo=github&style=for-the-badge)](https://github.com/linpingta/chinese-poem-generator/fork)
[![Clone](https://img.shields.io/badge/Clone-HTTPS-blue.svg)](https://github.com/linpingta/chinese-poem-generator.git)

# 安装
可以从pip上下载安装包：

	pip install ts_chinese_poem_generator

也可以下载源码后，安装到指定路径：

	python setup.py install --prefix=$HOME
项目依赖[jieba](https://github.com/fxsjy/jieba)提供分词服务，依赖[word2vec](https://radimrehurek.com/gensim/)提供词相似度计算。

# 使用
项目的主体内容均在generator.py中，安装依赖后，可以直接调用 python generator.py ，默认会遍历所有词牌，为每个词牌生成一首词。
在其它模块中引用类似如下方式：

	from poem_generator.generator import Generator
	
	
	class OmgPoemGenerator(object):
    	    def __init__(self, conf):
        	self.conf = conf

	    def generatePoem(self, title, tags, descriptions):
		logger = logging.getLogger('omg.poem')
		logger.info("generate poem begins")

		generator = Generator(basepath, self.conf)
		try:

		    # str to unicode
		    title = title.decode()
		    important_words = []
		    for tag in tags:
			important_words.append(tag.tag.decode())

		    logger.info("user input title %s, important_words %s, descriptions %s" % (title, str(important_words), str(descriptions)))
		    user_input_dict = dict(title=title, important_words=important_words, descriptions=descriptions, force_data_build=False)

		    # Init
		    generator.search_ratio = random.random() * 0.8
		    generator.force_data_build = user_input_dict["force_data_build"]
		    generator.init(logger)

		    # Generate poem
		    error_info = generator.check(user_input_dict, logger)
		    if not error_info:
			generator.title = user_input_dict["title"]
			generator.important_words = user_input_dict["important_words"]

			logger.info("generate poem for title %s, with important words %s" % (generator.title, str(generator.important_words)))
			result = generator.generate(logger)
		    else:
			result = error_info
		    logger.info("final generate poem %s" % result)
	      except ValueError as e:
		    logger.exception(e)
		except Exception as e:
		    logger.exception(e)
		finally:
		    return result.encode()

# 问题来源
我们拍了照片，把其中的物体关键字提取后（这个需要图片识别API，也可能有翻译API），把识别来的tag作为场景关键词，基于关键词做诗词创作。我们设想的一个场景是：在外旅游，看到大好风景却不知道如何描述。。拍一幅照片，让我们为你的微信朋友圈增加文艺范。

# 前期调研
目前较常见的自动创建软件（包括作诗，作词）主要是两条路：

    1.基于浅层的NLP和规则
    
    2.深度学习
  
同时我发现，无论是哪种方式，都没有依赖场景作词的情况：或者是随机生成，或者是生成藏头诗，因此依赖场景是本项目独特的部分。

词的格律比诗（五言七言）更多，挑战相对更大，选择词而不是诗，主要是因为我个人更喜欢词的表达方式。

我采用的是思路1。最终没有采用[深度学习的方案](https://github.com/karpathy/char-rnn)，主要是考虑黑客马拉松的项目，相关经验不足，在时间上很难来得及。

本项目的实现中使用了[ci-ren](https://github.com/LingDong-/ci-ren)的数据源，但实现逻辑完全不同。

# 工作
### 数据预处理

  	生成词牌名与平仄的关系
  
  	生成平仄与词语的关系
  
  	生成韵脚与词语的关系 （同时建立反向索引）
  
  	统计每个韵脚下的常用词
  
  	统计常用韵脚
  
  	Bigram以及建立查找索引
  
  	预分词 （依赖jieba）
  
  	计算词相关度（依赖gensim.word2vec）
  
通过数据的预处理，加速用户应用，同时具备强制重新预处理和自动预处理功能

### 关键词扩展

相比其它自动生成宋词的系统，我们的系统不仅是随机生成一组词，同时还要参考用户对场景的描述，即诗词的关键字。
通常情况下，用户的输入（很可能来自图片tag）是少量的，为了让词整体与用户输入更相关，我的想法是使得把词的每一句都包含关键词，而关键词又是与用户输入相关的，这样理论上既可以避免重复，也可以保证语境的一致性。
在网上调研后，我决定采用word2vec的相似度来描述词的相关性，同时word2vec需要输入分词后的句子，因此我采用[jieba](https://github.com/fxsjy/jieba)完成分词。

输入“菊花”，在model中的topN相似输出是：

    不容 0.995297551155
    时事 0.993381500244
    开尊 0.993283450603
    花开 0.993002593517
    自喜 0.992477238178
    恰 0.992455720901
    却是 0.99230247736
    辞荣 0.991610348225
    五日 0.99150288105

### 关键词填充

选出备选词后，我们遍历词牌里的每句话，考虑将它填充在合适的位置。因为我们还没有选韵脚，所以我们尽量填句子的开头，因为这样做可以给后面每句的完整生成留下更多的空间。此时要考虑平仄限制，同时也要考虑断句问题，比如七字句，通常的断句是2-2-3，2-2-1-2或者4-3，如果把一个两字词跨断位置填写（比如填在第2和3个字的位置），这样即使位置满足了，但整句读起来必然拗口。
粗略看了下，真实情况下宋词的短句原则是很复杂的，包括减字，摊破，时间有限，我只对每种句式规定了一些常用的位置划分，如果没有检查到，那么就不做位置上的检验，只做平仄检验。

### 韵脚选择

根据用户选择的词牌名，确定每句的韵脚。随机（加权）生成韵脚，以及韵脚关键词。
完成上述步骤后，我们在每句里至少有一个韵脚，通常还会有一个关键词。

### 诗词生成 （第一版）

每个句子独立生成，在生成句子前，填写基本的韵脚和随机位置的关键词，然后按字填写下一个字，每次填写一个字。
首先确定候选位置，候选位置指的是旁边（左侧或者右侧）已经填写了词的位置。从候选位置里随机选择一个位置，作为下一个要填写的词。
此时有可能某个位置左侧和右侧都有词，那么会以右侧为准。
选择字的原则是统计全宋词中词的bigram属性，分别统计以候选字开头和结尾的bigram属性。
此时生成的诗词，如《浣溪沙》：

  	    不知何如归去年,花开犹记当年年,年年华是太平生
	    次第一枝云深处,不如何万里扬州,来无庭院落花开
    
### 问题及更新
第一版看起来是十分不通顺的，为此我们增加了如下逻辑：

    	避免句间重复用词
	
    	控制句内重用词
	
   	关键词（相似词）提取逻辑更新
    
    	增加关键词相比韵脚的权重：诗句目前的生成，在每一步都是随机选择下一个生成点的，但关键词（假设准确）的权重实际应该高于韵脚，因为韵脚在初期是随机的，因此我们在有关键词的诗句里优先用关键词生成
    
    	考虑格式对填词来源的影响
 
 最终我们还增加了诗词标点和上下阕的区分，使得生成的词（尤其是比较长的词牌）变得较为易懂。
 
 最终测试一些类别的词牌：（这里是随机选择了一些）
 
      	输入： tags：[山川，流水]，title：浣溪沙
      	输出：

      	目送征帆双鸳鸯，一春回顾影风光，东西江上度刘郎
      	卷地久阿谁为寿，园林修竹是清香，依稀有意向沧浪
	
以及较长的词牌名：
      
       	输入： tags：[菊花，院子]，title：水调歌头
       	输出：
      
       	不踏青云酒,重数沈烟收.当时重九枯朽,烂醉里休休.细看花期惟有,邻里风流三友,不久长南楼.尽道分携手,三分付千秋.  
       	西北斗,须记取,杏梁州.渡江太守,健笔端正尔秦讴.七十五年祝寿,更把芳时开口,天远宦游流,日日登高首,受用处曾游.
 
### 其它
如果我们再加入一些trick，把部分语句的生成变成搜索问题（通过search_ratio控制，1表示全部优先考虑搜索，0表示全部自动生成），那么可读性方面会更多的提升：

      	声声慢 search_ratio = 0.74
      
      	洞房深处,香槽拨凤,有谁更赋惊鸿.罗绮成丛,榴花帘外飘红.渔人鸣榔归去,送春风`遥指征鸿.又何处,小溪愁无语,偶别珠宫.  
      	窗牖山川百虑,便千金慵觑,鸿雁晴空.云海匆匆,老夫鼻观先通.向晓洞开严署,一尊同`最是虫虫.功名誉,恨不著`落尽溪桐.
	
### 未来展望
最终这个项目相关的整个产品在公司的比赛中取得了第一名。

这方面目前国内最好的成果，应该来自[清华大学语音与语言实验中心](http://nlp.cslt.org/)提供的[作诗机](http://www.guancha.cn/Science/2016_03_21_354505.shtml)。他们的具体代码并没有开源，但可以确定是基于深度学习的递归神经网络（RNN）。所以从实际应用的角度讲，在深度学习方面多花时间，会优于按规则生成的方案，尤其是，如果我们需要把自动生成诗歌的目标转换为自动生成文案时，不再有韵脚格律的限制，规则的方法可能是会更受局限的（当然如果是生成五言广告语就忽略我）。


我认为从生成广告文案的目的讲，是有机会的，类比的例子是网上流传的“汪峰歌词机”，实际上就是基于[char-rnn](https://github.com/karpathy/char-rnn)替换文案源和参数的调用。当然，实际应用，肯定还有很多路要走。
