from setuptools import setup

setup(name='chinese_poem_generator',
	version='0.2',
	description='Chinese Poem Generator',
	url="https://github.com/linpingta/chinese-poem-generator.git",
	author='ChuTong',
	author_email='linpingta@163.com',
	license='MIT',
	packages=['poem_generator'],
	install_requires=[
		"jieba", "gensim"
	],
	zip_safe=False)
