#!/bin/bash

if [ -z "$1" ]; then
	# Look for ofending files excluding the current recording
	find /var/rotter/mp{2,3} -name *--*.mp* -exec "$0" {} \;
else
	# Hard link these files to more appropriate titles
	ln -v "$1" "$(echo "$1" | awk '{ gsub("--[[:digit:]]+", "-00"); print $0 }')"
	# Remove the offending file - rotter continues to write to the correct inode
	rm -v "$1"
fi
