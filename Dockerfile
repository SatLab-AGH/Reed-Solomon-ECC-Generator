FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/.local/bin:${PATH}"

# Install system dependencies from Ubuntu repositories
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    iverilog \
    curl \
    git \
    ca-certificates \
    build-essential \
    graphviz \
    gtkwave \
    yosys \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /workspace

# Copy dependency files early for caching
COPY pyproject.toml uv.lock* requirements*.txt* ./

# Install Python deps if present
RUN if [ -f pyproject.toml ]; then uv sync --active; fi

CMD ["/bin/bash"]