FROM debian:bookworm-slim

# https://github.com/jgraph/drawio-desktop/releases
ARG DRAWIO_VERSION=30.3.14

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        imagemagick \
        librsvg2-bin \
        xvfb xauth \
        wget ca-certificates \
        fonts-liberation fonts-noto-core fonts-dejavu-core \
        # runtime závislosti drawio-desktop (Electron)
        libasound2 libgtk-3-0 libnotify4 libnss3 libxss1 libxtst6 \
        libatspi2.0-0 libsecret-1-0 libgbm1 xdg-utils \
    && wget -q -O /tmp/drawio.deb \
        "https://github.com/jgraph/drawio-desktop/releases/download/v${DRAWIO_VERSION}/drawio-amd64-${DRAWIO_VERSION}.deb" \
    && apt-get install -y --no-install-recommends /tmp/drawio.deb \
    && rm /tmp/drawio.deb \
    && rm -rf /var/lib/apt/lists/*

# Wrapper: /usr/local/bin/drawio prekryje /usr/bin/drawio,
# spúšťa Electron headless cez xvfb-run a bez sandboxu.
COPY docker/drawio-wrapper.sh /usr/local/bin/drawio
RUN chmod +x /usr/local/bin/drawio

COPY src/ /opt/convoj/src/

# Electron potrebuje zapisovateľný HOME aj pri spustení s --user <uid>:<gid>
ENV HOME=/tmp \
    XDG_CONFIG_HOME=/tmp/.config \
    XDG_CACHE_HOME=/tmp/.cache

# projekt sa mountuje sem
WORKDIR /work

ENTRYPOINT ["python3", "/opt/convoj/src/convoj.py"]
CMD ["--help"]
