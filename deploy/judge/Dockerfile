ARG GO_JUDGE_IMAGE=criyle/go-judge:v1.13.3
FROM ${GO_JUDGE_IMAGE} AS runner

FROM debian:bookworm-slim
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    openjdk-17-jdk-headless g++ golang-go python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=runner /opt/go-judge /opt/go-judge
COPY mount.yaml /etc/go-judge/mount.yaml
WORKDIR /opt
ENTRYPOINT ["/opt/go-judge"]
