from setuptools import setup

setup(name='poem_generator',
	version='0.1',
	description='Poem Generator',
	author='ChuTong',
	author_email='linpingta@163.com',
	license='MIT',
	packages=['poem_generator'],
	install_requires=[
		"jieba", "gensim"
	]
	zip_safe=False)
