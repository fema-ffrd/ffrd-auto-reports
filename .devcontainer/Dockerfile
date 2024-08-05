FROM mambaorg/micromamba:1.5.6

# Install libgdal-dev
USER root
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Add the current directory contents into the container at /tmp
COPY --chown=$MAMBA_USER:$MAMBA_USER env.yaml /tmp/env.yaml

# Clean up
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Install the environment with micromamba
RUN micromamba install -y -n base -f /tmp/env.yaml && \
    micromamba clean --all --yes
