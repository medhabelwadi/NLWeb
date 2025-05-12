#!/usr/bin/env bash

# set up virutal environment
python -m venv myenv
source myenv/bin/activate 

# install dependencies
pushd ./code || exit
  pip install --upgrade pip
  pip install -r requirements.txt
popd || exit

# install tflint
curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash