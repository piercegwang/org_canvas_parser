##
# org_canvas_parser
#
# @file
# @version 0.1

PYTHON_VERSION=3.11

venv:
	python -m venv py${PYTHON_VERSION}
	py${PYTHON_VERSION}/bin/python -m pip install -r requirements.txt

# end
