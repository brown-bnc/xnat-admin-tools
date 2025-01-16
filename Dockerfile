FROM python:3.11.8

WORKDIR /xnat-admin-tools

COPY poetry.lock pyproject.toml xnat_admin_tools ./
COPY xnat_admin_tools/ ./xnat_admin_tools

RUN pip install .