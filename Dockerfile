FROM python:3.9.5

WORKDIR /xnat-admin-tools
RUN mkdir -p 
WORKDIR xnat-admin-tools

COPY poetry.lock pyproject.toml xnat_admin_tools ./
COPY xnat_admin_tools/ ./xnat_admin_tools

RUN pip install .