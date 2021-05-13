VIZ_HOME ?= ${PWD}
# VIZ_PRODUCTION = "0" # For development and testing purposes
VIZ_PRODUCTION ?= "1"
HOSTNAME ?= $(shell hostname)
# Check if the source is a git repo
GITREPO := $(wildcard .git)

.PHONY: doc default

all: default doc

default:
	# Note that IMAS is required!
	# In case the VIZ repository was cloned, update the submodules (e.g. ETSViz)
	$(if ${GITREPO},git submodule init; git submodule update)
	# Generate IDSDef_XMLParser_Generated_<IMAS_VERSION>.py files
	export VIZ_HOME=${VIZ_HOME}; \
	export VIZ_PRODUCTION=${VIZ_PRODUCTION}; \
	export HOSTNAME=${HOSTNAME}; \
	python3 ${VIZ_HOME}/imasviz/VizDataAccess/VizCodeGenerator/QVizDataAccessCodeGenerator.py

doc:
	# Generate PDF and HTML documentation
	# Note: on the Gateway and ITER HPC first loading the "texlive" module is
	# required
	# module load texlive
	cd ${VIZ_HOME}/doc; \
	make html; \
	make latexpdf

clean:
	rm -rf ${HOME}/.imasviz/VizGeneratedCode
	rm -rf ${VIZ_HOME}/doc/build
