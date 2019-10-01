VIZ_HOME = ${PWD}
# VIZ_PRODUCTION = "0" # For development and testing purposes
VIZ_PRODUCTION = "1"
HOSTNAME = $(shell hostname)

default:
	# Generate IDSDef_XMLParser_Generated_<IMAS_VERSION>.py files
	mkdir -p ${VIZ_HOME}/imasviz/VizDataAccess/VizGeneratedCode
	export VIZ_HOME=${VIZ_HOME}; \
	export VIZ_PRODUCTION=${VIZ_PRODUCTION}; \
	export HOSTNAME=${HOSTNAME}; \
	python3 ${VIZ_HOME}/imasviz/VizDataAccess/VizCodeGenerator/QVizDataAccessCodeGenerator.py