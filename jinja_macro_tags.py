from jinja2 import (nodes, BaseLoader, ChoiceLoader, PrefixLoader, FileSystemLoader,\
                    PackageLoader, TemplateNotFound)
from jinja2.ext import Extension
import re
import os


def configure_environment(env, wrap_loader=True, with_jinja_tags=True, with_html_tags=True):
    if wrap_loader:
        env.loader = MacroLoader(env.loader)
    env.add_extension(LoadMacroExtension)
    env.add_extension(CallMacroTagExtension)
    if with_jinja_tags:
        env.add_extension(JinjaMacroTagsExtension)
    if with_html_tags:
        env.add_extension(HtmlMacroTagsExtension)


def parse_macro_tag_signature(parser):
    args = []
    kwargs = []

    while parser.stream.current.type != "block_end":
        if parser.stream.current.type == "name" and \
           parser.stream.look().type == "assign":
            key = parser.stream.current.value
            parser.stream.skip(2)
            value = parser.parse_expression()
            kwargs.append(nodes.Keyword(key, value, lineno=value.lineno))
        else:
            args.append(parser.parse_expression())

    return args, kwargs


class FileLoader(BaseLoader):
    def __init__(self, filename, alias=None):
        self.filename = filename
        alias = alias or os.path.basename(filename)
        if not isinstance(alias, (tuple, list)):
            alias = [alias]
        self.aliases = alias

    def get_source(self, environment, template):
        if template in self.aliases:
            with open(self.filename) as f:
                source = f.read()
            return source, template, None
        raise TemplateNotFound(template)

    def list_templates(self):
        return self.aliases


class MacroLoader(ChoiceLoader):
    def __init__(self, loader=None):
        self.loader = loader
        self.macro_loaders = []
        self.prefix_loader = PrefixLoader({"__macros__": ChoiceLoader(self.macro_loaders)})
        super(MacroLoader, self).__init__([self.loader, self.prefix_loader])


class MacroRegistry(object):
    macro_regexp = re.compile(r"\{% macro ([a-zA-Z_0-9]+)")

    def __init__(self, environment):
        super(MacroRegistry, self).__init__()
        self.environment = environment
        self.templates = {}
        self.aliases = {}

    def register(self, name, template, replace=False):
        if not replace and name in self.templates:
            raise Exception("Macro '%s' is already declared in '%s'" % (name, self.templates[name]))
        self.templates[name] = template

    def register_from_source(self, source, template, replace=False):
        for m in self.macro_regexp.finditer(source):
            self.register(m.group(1), template, replace)

    def register_from_template(self, template, replace=False):
        source, _, _ = self.environment.loader.get_source(self.environment, template)
        self.register_from_source(source, template, replace)

    def register_from_environment(self):
        try:
            templates = self.environment.list_templates(extensions=("html",))
        except TypeError:
            return
        for tpl in templates:
            self.register_from_template(tpl)

    def register_from_dir(self, path, replace=False):
        for root, dirs, files in os.walk(path):
            for f in files:
                self.register_from_file(os.path.join(root, f), replace)

    def register_loader(self, loader, prefix=None, replace=False):
        if not isinstance(self.environment.loader, MacroLoader):
            raise Exception("The macro system requires the Jinja loader to be wrapped using an instance of MacroLoader")
        if prefix:
            loader = PrefixLoader(dict([(prefix, loader)]))
        self.environment.loader.macro_loaders.append(loader)
        for tpl in loader.list_templates():
            self.register_from_template("__macros__/" + tpl, replace)

    def register_file(self, path, alias=None, replace=False):
        self.register_loader(FileLoader(path, alias), replace=replace)

    def register_directory(self, path, prefix=None, replace=False):
        self.register_loader(FileSystemLoader(path), prefix, replace)

    def register_package(self, package_name, package_path="macros", prefix=None, replace=False):
        self.register_loader(PackageLoader(package_name, package_path), prefix, replace)

    def alias(self, name, alias):
        self.aliases[alias] = name

    def resolve_alias(self, name):
        return self.aliases.get(name, name)

    def resolve_template(self, name):
        return self.templates.get(name)

    def resolve(self, name):
        name = self.resolve_alias(name)
        tpl = self.resolve_template(name)
        if not tpl:
            return None, None
        return name, tpl

    def exists(self, name):
        return name in self.aliases or name in self.templates


class LoadMacroExtension(Extension):
    tags = set(["load_macro"])

    def __init__(self, environment):
        super(LoadMacroExtension, self).__init__(environment)
        environment.extend(macros=MacroRegistry(environment))

    def parse(self, parser):
        lineno = parser.stream.next().lineno

        args = []
        require_comma = False
        while parser.stream.current.type != 'block_end':
            if require_comma:
                parser.stream.expect('comma')
                # support for trailing comma
                if parser.stream.current.type == 'block_end':
                    break
            args.append(parser.parse_expression())
            require_comma = True

        if not args:
            return []

        templates = {}
        for arg in args:
            if not isinstance(arg, nodes.Name):
                raise Exception("load_macro tag expects a list of macro names")
            if not self.environment.macros.exists(arg.name):
                # jinja will raise an error at runtime
                continue
            name, tpl = self.environment.macros.resolve(arg.name)
            if name is None:
                continue
            templates.setdefault(tpl, set())
            templates[tpl].add(name)

        imports = []
        for tpl, macros in templates.iteritems():
            imports.append(nodes.FromImport(nodes.Const(tpl), macros, True, lineno=lineno))

        return imports


class CallMacroTagExtension(Extension):
    tags = set(["macro_tag", "call_macro_tag"])

    def parse(self, parser):
        is_block = parser.stream.current.test("name:call_macro_tag")
        lineno = parser.stream.next().lineno
        macro_name = self.environment.macros.resolve_alias(parser.stream.current.value)
        parser.stream.next()
        args, kwargs = parse_macro_tag_signature(parser)

        call = nodes.Call(nodes.Name(macro_name, "load"), args, kwargs, None, None, lineno=lineno)
        if is_block:
            body = parser.parse_statements(['name:endmacrotag'], drop_needle=True)
            return nodes.CallBlock(call, [], {}, body, lineno=lineno)
        return nodes.Output([call])


class JinjaMacroTagsExtension(Extension):
    tag_regexp = re.compile(r"<\{\s*([a-zA-Z_0-9]+)")
    close_block_regexp = re.compile(r"</\{(\s*([a-zA-Z_0-9]+)\s*)?\}>")

    def preprocess(self, source, name, filename=None):
        return preprocess_macro_tags(source, self.tag_regexp, "}/>", "}>", self.close_block_regexp)


class HtmlMacroTagsExtension(CallMacroTagExtension):
    tag_regexp = re.compile(r"<m:([a-zA-Z_0-9\-]+)")
    close_block_regexp = re.compile(r"</m:([a-zA-Z_0-9\-]+)?>")

    def preprocess(self, source, name, filename=None):
        return preprocess_macro_tags(source, self.tag_regexp, "/>", ">", self.close_block_regexp)


def preprocess_macro_tags(source, tag_regexp, tag_closing_char, block_closing_char, close_block_regexp):
    macros = set()
    source = replace_macro_tags(source, tag_regexp, tag_closing_char, block_closing_char, macros)
    source = close_block_regexp.sub(r"{% endmacrotag %}", source)
    if macros:
        source = "{%% load_macro %s %%}\n%s" % (", ".join(macros), source)
    return source


def replace_macro_tags(source, regexp, tag_closing_char, block_closing_char, macros):
    orig_source = source
    r = regexp.search(orig_source)
    if r:
        source = ""
        pos = 0
        while r:
            name = r.group(1).replace("-", "_")
            macros.add(name)
            source += orig_source[pos:r.start()]
            pos = r.end()
            close_pos, close_char = find_closing(orig_source, (block_closing_char, tag_closing_char), pos)
            if close_pos == -1:
                raise Exception("Missing closing bracket for %s" % name)
            func = "call_macro_tag" if close_char == block_closing_char else "macro_tag"
            source += "{% " + func + " " + name + " " + orig_source[pos:close_pos].strip() + " %}"
            pos = close_pos + len(close_char)
            r = regexp.search(orig_source, pos)
        source += orig_source[pos:]
    return source


def find_closing(source, chars, start=0):
    str_open_pos, str_open_char = find_next_char(source, ("'", '"'), start)
    next_char_pos, next_char = find_next_char(source, chars, start)
    if next_char_pos == -1:
        return (-1, "")
    if str_open_pos == -1 or next_char_pos < str_open_pos:
        return (next_char_pos, next_char)

    pos = str_open_pos + 1
    while True:
        str_close = source.find(str_open_char, pos)
        if str_close == -1:
            return (-1, "")
        if source[str_close - 1] == "\\": # character is escaped
            pos = str_close + 1
        else:
            break
    return find_closing(source, chars, str_close + 1)


def find_next_char(source, chars, start=0):
    indexes = [(c, source.find(c, start)) for c in chars]
    min_index = None
    char = None
    for c, i in indexes:
        if i > -1 and (min_index is None or i < min_index):
            min_index = i
            char = c
    if min_index is None:
        return (-1, "")
    return (min_index, char)