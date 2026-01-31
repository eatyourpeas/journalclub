FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git ffmpeg libsndfile1 ca-certificates wget unzip \
    espeak-ng libespeak-ng1 \
    && rm -rf /var/lib/apt/lists/*

# Install rustup (non-interactive)
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y && \
    # ensure cargo in PATH for subsequent RUN commands
    echo 'export CARGO_HOME="$HOME/.cargo"' >> /etc/profile.d/cargo.sh && \
    echo 'export RUSTUP_HOME="$HOME/.rustup"' >> /etc/profile.d/cargo.sh && \
    echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> /etc/profile.d/cargo.sh && \
    . $HOME/.cargo/env && rustc --version || true

WORKDIR /app

COPY docker/coqui/requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel && \
    # ensure PATH includes cargo for pip build steps
    export PATH="$HOME/.cargo/bin:$PATH" && \
    pip install --no-cache-dir -r requirements.txt

COPY docker/coqui/app.py /app/app.py

EXPOSE 5002

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5002"]
