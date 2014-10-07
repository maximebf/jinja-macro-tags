# Jinja Macro Tags

Jinja Macro Tags introduces a new syntax to call macros as well
as an automatic macro loader.

## Installation

    pip install jinja-macro-tags

## Macro tags

Macro tags allow you to use Jinja's macros with a syntax similar
to html tags. There are two types of macro tags: inline and block.
Inline is the equivalent of calling the macro using `{{ macro_name() }}`
and block is equivalent to the `{% call %}` directive.

Inline directives are enclosed in `<{` and `}/>`. Arguments
can be provided the same was as html attributes but their values are
Jinja expressions.

Inline tag example:

    <{macro_name arg1=value1 arg2=value2 }/>

is equivalent to:

    {{ macro_name(arg1=value1, arg2=value2) }}

Block tags, start with an opening directive enclosed in `<{` and `}>`
and must be closed with a closing directive `</{macro_name}>` (note
that the macro name is optional in the closing directive).

Block tag example:

    <{macro_name arg1=value1 arg2=value2 }>
        my macro content
    </{macro_name}>

is equivalent to:

    {% call macro_name(arg1=value1, arg2=value2) %}
        my macro content
    {% endcall %}

To use macro tags, you'll need to add the `jinja_macro_tags.CallMacroTagExtension`
and `jinja_macro_tags.JinjaMacroTagsExtension` extensions to your
environment.

    from jinja2 import Environment, PackageLoader

    env = Environment(loader=PackageLoader(__name__, 'templates'))
    env.add_extension('jinja_macro_tags.CallMacroTagExtension')
    env.add_extension('jinja_macro_tags.JinjaMacroTagsExtension')

(Note that this does not autoload macros, you will still need to
include your `import` statements)

## Macro registry

The macro registry allows you to load macros by name. Macros can
be registered from templates but also from any jinja files not
accessible from your loader.

When using in conjunction with macro tags, you don't even need
to load macros, the macro tags will use the registry to automatically
load them.

The registry requires two things:

 - wrapping your template loader in an instance of
   `jinja_macro_tags.MacroLoader`
 - adding the `jinja_macro_tags.LoadMacroExtension` extension.

To make things easier you can use the `configure_environment`
function. It will automatically wrap the environment loader
and add the extension. By default, it will also add the
`CallMacroTagExtension` and the `JinjaMacroTagsExtension`
extensions but this can be disabled with `with_jinja_tags=False`.

    from jinja2 import Environment, PackageLoader
    from jinja_macro_tags import configure_environment

    env = Environment(loader=PackageLoader(__name__, 'templates'))
    configure_environment(env)

Without macro tags:

    configure_environment(env, with_jinja_tags=False)

Once configured, you can register macros against the macro
registry available through the `macros` attribute of the environment.

You can register macros from templates available through your loader:

 - `register_from_template(template)`: register all macros defined
   in the template
 - `register(name, template)`: register the specified macro located
   in the template
 - `register_from_environment()`: look for macros in every templates

You can also register macros using templates not accessible from
your environment loader:

 - `register_file(filename)`
 - `register_directory(path)`
 - `register_package(package_name, package_path='macros')`

Note that files added using this methods, will be accessible from
your environment using the *__macros__* prefix.  
You can create macro aliases using the `alias(name, alias)` method.

To load your macros, use the `load_macro` directive which takes a
list of macro names as arguments:

    {% load_macro form_tag, form_field %}

Once again, no need to use this directive if you are using macro tags.

## Full example

In *app.py*:

    from jinja2 import Environment, PackageLoader
    from jinja_macro_tags import configure_environment

    env = Environment(loader=PackageLoader(__name__, 'templates'))
    configure_environment(env)
    env.macros.register_file('macros.html')

    print env.get_template('form.html').render()

In *macros.html*:

    {% macro form_tag(action) %}
        <form action="{{ action }}" method="post">
            {{ caller() }}
        </form>
    {% endmacro %}

    {% macro form_input(name) %}
        <input type="text" name="{{ name }}">
    {% endmacro %}

In *templates/form.html*:

    <{form action="/" }>
        <{form_input name="email" }/>
    </{form}>