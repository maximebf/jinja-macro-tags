from setuptools import setup


setup(
    name='jinja-macro-tags',
    version='0.1',
    url='http://github.com/frascoweb/jinja-macro-tags',
    license='MIT',
    author='Maxime Bouroumeau-Fuseau',
    author_email='maxime.bouroumeau@gmail.com',
    description='Macro loader and tag system to call macros',
    py_modules=['jinja_macro_tags'],
    platforms='any',
    install_requires=['jinja2']
)