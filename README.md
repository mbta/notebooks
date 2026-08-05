# Notebooks

Marimo and/or other notebooks for users at the MBTA.

## Dependencies
[uv](https://docs.astral.sh/uv/). 

If you're using [mise](https://mise.jdx.dev/) to manage your developer tools, you can install this dependency by running `mise install` in the repository.

This repository assumes you already have access to [Lightswitch](https://github.com/mbta/lamp/blob/main/src/lamp_py/publishing/README.md). If you do not, follow the steps for getting access there.

## Usage

The root project contains a [Copier template](https://copier.readthedocs.io/) that will create a notebook for you.

1. `uv run copier notebook_template my_user_folder` where `my_user_folder` is the folder where you want all of your notebooks to live
2. This will prompt you to name your notebook, and will create a folder structure containing a new project
3. Follow the instructions in your new notebook's `README.md`


