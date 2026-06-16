ARG ISAACLAB_BASE_IMAGE_ARG=nvcr.io/nvidia/isaac-lab:2.3.2

FROM ${ISAACLAB_BASE_IMAGE_ARG} AS base

ARG DOCKER_TABERO_PATH_ARG=/workspace/tabero
ENV DOCKER_TABERO_PATH=${DOCKER_TABERO_PATH_ARG} \
    ACCEPT_EULA=Y \
    PRIVACY_CONSENT=Y \
    OMNI_KIT_ALLOW_ROOT=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

USER root

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

RUN printf '%s\n' '#!/usr/bin/env bash' 'exec /workspace/isaaclab/_isaac_sim/python.sh "$@"' > /usr/local/bin/python && \
    chmod +x /usr/local/bin/python && \
    ln -sf /usr/local/bin/python /usr/local/bin/python3 && \
    printf '%s\n' '#!/usr/bin/env bash' 'exec /workspace/isaaclab/_isaac_sim/python.sh -m pip "$@"' > /usr/local/bin/pip && \
    chmod +x /usr/local/bin/pip && \
    ln -sf /usr/local/bin/pip /usr/local/bin/pip3

# Copy the Tabero repository into the image. Files to exclude are defined in .dockerignore.
COPY . ${DOCKER_TABERO_PATH}

RUN bash -lc "source ${HOME}/.bashrc && \
    cd ${DOCKER_TABERO_PATH} && \
    python -m pip install --upgrade pip && \
    python -m pip install \
      -e source/tac_manip \
      -e benchmarks/openpi/openpi-client \
      pytest \
      tyro \
      h5py \
      opencv-python-headless \
      tqdm \
      matplotlib"

WORKDIR ${DOCKER_TABERO_PATH}
