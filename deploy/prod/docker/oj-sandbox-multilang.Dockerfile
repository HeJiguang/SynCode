FROM debian:bookworm-slim

ARG DEBIAN_MIRROR=deb.debian.org
RUN if [ "$DEBIAN_MIRROR" != "deb.debian.org" ]; then \
        sed -i "s/deb.debian.org/$DEBIAN_MIRROR/g" /etc/apt/sources.list.d/debian.sources; \
    fi

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        g++ \
        golang-go \
        openjdk-17-jdk-headless \
        python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/share/java

CMD ["sh", "-c", "while true; do sleep 3600; done"]
