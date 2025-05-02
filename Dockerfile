FROM python:3.12

WORKDIR /workspace

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends curl git less && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/pip-tmp/

RUN pip --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp

ENV OPENAPI_URL=/openapi.json

COPY app /workspace/app
COPY tests /workspace/tests

ENV OPENAPI_URL=/openapi.json

ARG USERNAME=api
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME
USER $USERNAME

EXPOSE 8000
# Set the default shell to bash instead of sh
ENV SHELL /bin/bash
