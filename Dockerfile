# syntax=docker/dockerfile:1

FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends clang cmake ninja-build python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY . .

RUN cmake -S . -B build-docker -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_COMPILER=clang++ \
      -DBUILD_EXAMPLES=OFF \
    && cmake --build build-docker --parallel 2 --target \
      zi_wei_web_cli qi_men_web_cli ba_zi_web_cli liu_yao_web_cli da_liu_ren_web_cli

FROM ubuntu:24.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin zhouyi

WORKDIR /app
COPY --from=builder /src/web ./web
COPY --from=builder /src/config ./config
COPY --from=builder /src/build-docker/examples/*_web_cli ./build/examples/
RUN mkdir -p /app/.zhouyilab \
    && chown -R zhouyi:zhouyi /app

USER zhouyi
EXPOSE 8768
VOLUME ["/app/.zhouyilab"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8768/api/v1/health', timeout=3)"

CMD ["python3", "web/server.py", "--port", "8768"]
