VIZ_HOME ?= ${PWD}
# For development and testing purposes, set to 0:
# VIZ_PRODUCTION = 0
VIZ_PRODUCTION ?= 1
HOSTNAME ?= $(shell hostname)
export VIZ_HOME VIZ_PRODUCTION HOSTNAME
# Check if the source is a git repo
GITREPO := $(wildcard .git)

.PHONY: doc default

all: default doc

default:
	# Note that IMAS is required!
	# In case the VIZ repository was cloned, update the submodules (e.g. ETSViz)
	@if [ -n "${GITREPO}" ]; then \
		git submodule init && git submodule update && echo "submodules updated" || echo "could not obtain all submodules, Viz may miss some plugins"; \
	else \
		echo "could not obtain all submodules, Viz may miss some plugins"; \
	fi

doc:
	# Generate PDF and HTML documentation
	# Note: on the Gateway and ITER HPC first loading the "texlive" module is
	# required (module load texlive)
	cd ${VIZ_HOME}/doc; \
	make html; \
	#make latexpdf

clean:
	rm -rf ${HOME}/.imasviz/VizGeneratedCode
	rm -rf ${VIZ_HOME}/doc/build
