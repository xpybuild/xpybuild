# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from typing import List, Dict, Tuple

DOC_SOURCE_DIR = os.path.dirname(__file__)
XPYBUILD_ROOT_DIR = os.path.abspath(DOC_SOURCE_DIR+'/..')

sys.path.append(XPYBUILD_ROOT_DIR)

# -- Project information -----------------------------------------------------

copyright = '2019-2021, Ben Spiller and Matthew Johnson'
author = 'Ben Spiller and Matthew Johnson'

# The full version, including alpha/beta/rc tags
with open(XPYBUILD_ROOT_DIR+'/xpybuild/XPYBUILD_VERSION') as versionfile:
	release = versionfile.read().strip()

project = f'xpybuild v{release}'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
	'sphinx.ext.autodoc',
	'sphinx.ext.autosummary',
	'sphinx.ext.viewcode',
	'sphinx_epytext',
	'sphinxcontrib_autodocgen',
]

default_role = 'py:obj' # So that `xxx` is converted to a Python reference. Use ``xxx`` for monospaced non-links.

autoclass_content = 'both' # include __init__ params in doc strings for class

autodoc_inherit_docstrings = False # otherwise we end up with every target redeclaring run/clean/etc

autodoc_member_order = 'bysource' # bysource is usually a more logical order than alphabetical

autodoc_default_options = {
	'show-inheritance':True, # show base classes
    #'members': 'var1, var2',
    #'member-order': 'bysource',
    #'special-members': '__init__',
    #'undoc-members': True,
    # The supported options are 'members', 'member-order', 'undoc-members', 'private-members', 'special-members', 'inherited-members', 'show-inheritance', 'ignore-module-all', 'imported-members' and 'exclude-members'.
    #'exclude-members': '__weakref__'
}

#nitpicky = True # so we get warnings about broken links

from sphinx.util import logging
logger = logging.getLogger('conf.py')

def autodoc_skip_member(app, what, name, obj, skip, options):
	# nb: 'what' means the kind of member e.g. 'class'

	#logger.info(f'autodoc_skip_member: what={what}, name={name}, obj={obj}, skip="{skip}')

	# todo: implement private skipping
	if skip: 
		logger.debug(f'conf.py: ALREADY Skipping member: {name}')
		return None

	if obj.__doc__ and '.. private:: ' in obj.__doc__: 
		logger.info(f'conf.py: skipping private member: {obj}')
		return True
		
	return None

def process_docstring_fixEpydocIndentation(app, what, name, obj, options, lines):
	# unlike epydoc, sphinx requires indentation for multi-line values; auto-add it
	
	# this processor is invoked after epydoc @xxx are converted to :xxx sphinx directives
	
	indirective = False
	i = 0
	for l in lines:
		stripped = l.lstrip()
		if stripped.startswith(':'):
			indirective = True
		elif len(stripped)==0:
			indirective = False
		elif indirective:
			lines[i] = '   '+lines[i]
	
		i+=1

	# Sphinx v2 used to require us to use "~." syntax for class instance vars; this looks wrong in the more recent sphinx versions 
	# so until we know all downstream users of PySys have upgraded Sphinx, keep the docstrings the same and dynamically pre-process them
	# To check this, see any class with instance variables e.g. Process
	for i, l in enumerate(lines):
		if ':ivar ' in l and ' ~.' in l:
			lines[i] = l.replace(' ~.', ' ')


# Since we already add headings for autodoc entries, stop Sphinx from creating duplicate ones underneath
toc_object_entries = False

#autosummary_generate = True

import xpybuild
autodocgen_config = { # Configuration format is defined by sphinx_autodocgen.AutoDocGen.Config
	'modules':['xpybuild'],
	'generated_source_dir': DOC_SOURCE_DIR+'/autodocgen/',
	'skip_module_regex': '(xpybuild[.]internal.*|.*[.]__)', # if module matches this then it and any of its submodules will be skipped
	'write_documented_items_output_file': XPYBUILD_ROOT_DIR+'/_build_output/docs/autodocgen_documented_items.txt',
	'autodoc_options_decider': {
		'xpybuild.utils.outputhandler.ProcessOutputHandler': {'members':True, 'private-members':True},
	},
}

def setup(app):
	app.connect("autodoc-skip-member", autodoc_skip_member)

	app.connect('autodoc-process-docstring', process_docstring_fixEpydocIndentation)

	def supportGitHubPages(app, exception):
		outputdir = os.path.abspath('./html')
		open(outputdir+'/.nojekyll', 'wb').close()
	app.connect('build-finished', supportGitHubPages)


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme' # read-the-docs theme looks better than the default "classic" one but has bugs e.g. no table wrapping

html_theme_options = {
    #'display_version': True,
    #'prev_next_buttons_location': 'bottom',
    #'style_external_links': False,
    #'vcs_pageview_mode': '',
    #'style_nav_header_background': 'white',
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    #'navigation_depth': 4,
    'includehidden': False,
    #'titles_only': False
}


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_css_files = [
	# Workaround for RTD 0.4.3 bug https://github.com/readthedocs/sphinx_rtd_theme/issues/117
	'theme_overrides.css',  # override wide tables in RTD theme
]
