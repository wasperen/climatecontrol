from setuptools import setup

setup(
    name='climatecontrol',
    version='0.0.1',
    packages=['venv.lib.python3.7.site-packages.cffi', 'venv.lib.python3.7.site-packages.idna',
              'venv.lib.python3.7.site-packages.paho', 'venv.lib.python3.7.site-packages.paho.mqtt',
              'venv.lib.python3.7.site-packages.pytz', 'venv.lib.python3.7.site-packages.yaml',
              'venv.lib.python3.7.site-packages.yarl', 'venv.lib.python3.7.site-packages.bcrypt',
              'venv.lib.python3.7.site-packages.jinja2', 'venv.lib.python3.7.site-packages.aiohttp',
              'venv.lib.python3.7.site-packages.certifi', 'venv.lib.python3.7.site-packages.chardet',
              'venv.lib.python3.7.site-packages.chardet.cli', 'venv.lib.python3.7.site-packages.iso8601',
              'venv.lib.python3.7.site-packages.urllib3', 'venv.lib.python3.7.site-packages.urllib3.util',
              'venv.lib.python3.7.site-packages.urllib3.contrib',
              'venv.lib.python3.7.site-packages.urllib3.contrib._securetransport',
              'venv.lib.python3.7.site-packages.urllib3.packages',
              'venv.lib.python3.7.site-packages.urllib3.packages.rfc3986',
              'venv.lib.python3.7.site-packages.urllib3.packages.backports',
              'venv.lib.python3.7.site-packages.urllib3.packages.ssl_match_hostname',
              'venv.lib.python3.7.site-packages.requests', 'venv.lib.python3.7.site-packages.appdaemon',
              'venv.lib.python3.7.site-packages.appdaemon.plugins',
              'venv.lib.python3.7.site-packages.appdaemon.plugins.hass',
              'venv.lib.python3.7.site-packages.appdaemon.plugins.mqtt', 'venv.lib.python3.7.site-packages.multidict',
              'venv.lib.python3.7.site-packages.pycparser', 'venv.lib.python3.7.site-packages.pycparser.ply',
              'venv.lib.python3.7.site-packages.websocket', 'venv.lib.python3.7.site-packages.websocket.tests',
              'venv.lib.python3.7.site-packages.markupsafe', 'venv.lib.python3.7.site-packages.voluptuous',
              'venv.lib.python3.7.site-packages.async_timeout', 'venv.lib.python3.7.site-packages.aiohttp_jinja2',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.idna',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.pytoml',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.certifi',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.chardet',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.chardet.cli',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.distlib',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.distlib._backport',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.msgpack',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.urllib3',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.urllib3.util',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.urllib3.contrib',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.urllib3.contrib._securetransport',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.urllib3.packages',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.urllib3.packages.backports',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.urllib3.packages.ssl_match_hostname',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.colorama',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.html5lib',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.html5lib._trie',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.html5lib.filters',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.html5lib.treewalkers',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.html5lib.treeadapters',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.html5lib.treebuilders',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.lockfile',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.progress',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.requests',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.packaging',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.cachecontrol',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.cachecontrol.caches',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.webencodings',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._vendor.pkg_resources',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._internal',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._internal.req',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._internal.vcs',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._internal.utils',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._internal.models',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._internal.commands',
              'venv.lib.python3.7.site-packages.pip-10.0.1-py3.7.egg.pip._internal.operations'],
    url='https://github.com/wasperen/climatecontrol',
    license='MIT',
    author='wasperen',
    author_email='',
    description=''
)
