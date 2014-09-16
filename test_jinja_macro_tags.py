import unittest
from jinja2 import Environment, FileSystemLoader
from jinja_macro_tags import (MacroLoader, LoadMacroExtension, CallMacroTagExtension,\
                              JinjaMacroTagsExtension, HtmlMacroTagsExtension)
import os


templates_path = os.path.join(os.path.dirname(__file__), "test-templates")


class JinjaMacroTagTestCase(unittest.TestCase):
    def setUp(self):
        self.env = Environment(loader=FileSystemLoader(templates_path))
        self.env.add_extension(LoadMacroExtension)
        self.env.add_extension(CallMacroTagExtension)
        self.env.add_extension(JinjaMacroTagsExtension)
        self.env.add_extension(HtmlMacroTagsExtension)

    def test_register_macro_from_template(self):
        self.env.macros.register_from_template("macros.html")
        self.assertTrue(self.env.macros.exists("panel"))

    def test_register_macro_from_file(self):
        def register_file():
            self.env.macros.register_file(os.path.join(templates_path, "macros.html"))
        self.assertRaises(Exception, register_file)
        self.env.loader = MacroLoader(self.env.loader)
        register_file()
        self.assertTrue(self.env.macros.exists("panel"))

    def test_jinja_macro_tag(self):
        self.env.macros.register_from_template("macros.html")
        tpl = self.env.get_template("jinja_style.html")
        self.assert_html(tpl.render())

    def test_html_macro_tag(self):
        self.env.macros.register_from_template("macros.html")
        tpl = self.env.get_template("html_style.html")
        self.assert_html(tpl.render())

    def assert_html(self, html):
        print html
        self.assertIn('<div class="panel-title">test panel</div>', html)
        self.assertIn('<div><button type="button" class="btn btn-default">click me</button></div>', html)
        self.assertIn('<button type="button" class="btn btn-primary">click me</button>', html)


if __name__ == '__main__':
    unittest.main()