#!/usr/bin/env python

from distutils.core import setup

setup(
	name="mclogalyzer",
	version="1.1",
	description="Minecraft Server Log Analyzer",
	author="Moritz Hilscher",
	author_email="moritz.hilscher@gmail.com",
	license="GNU General Public License v3",
	url="http://github.com/m0r13/mclogalyzer",
	packages=["mclogalyzer"],
	package_data={"mclogalyzer" : ["template.html"]},
	scripts=["bin/mclogalyzer"],
)
