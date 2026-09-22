# syntax=docker/dockerfile:1

ARG BUILDER_IMAGE=silkeh/clang:20
ARG RUNTIME_IMAGE=ubuntu:24.04
ARG BUILD_JOBS=auto

FROM ${BUILDER_IMAGE} AS builder

ARG BUILD_JOBS=auto

ENV DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    --mount=type=cache,target=/root/.cache/pip \
    apt-get update \
    && apt-get install -y --no-install-recommends cmake ninja-build python3 python3-pip ca-certificates \
    && pip3 install --break-system-packages 'cmake>=3.28'

WORKDIR /src
COPY . .

RUN jobs="${BUILD_JOBS}"; if [ "$jobs" = "auto" ]; then jobs="$(nproc)"; fi; \
    cmake -S . -B build-docker -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_CXX_COMPILER=clang++ \
      -DBUILD_EXAMPLES=OFF \
    && cmake --build build-docker --parallel "$jobs" --target \
      zi_wei_web_cli qi_men_web_cli ba_zi_web_cli liu_yao_web_cli da_liu_ren_web_cli mei_hua_web_cli common_calendar_web_cli astro_web_cli

FROM ${RUNTIME_IMAGE} AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ZHOUYILAB_BIND_HOST=0.0.0.0 \
    ZHOUYILAB_EPHEMERIS_PATH=/app/data/ephemeris
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates libc++1 libc++abi1 \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin zhouyi

WORKDIR /app
COPY --from=builder /src/web/requirements.txt ./web/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install --break-system-packages -r ./web/requirements.txt
COPY --from=builder /src/web ./web
COPY --from=builder /src/config ./config
COPY --from=builder /src/data/ephemeris ./data/ephemeris
COPY --from=builder /src/data/geo ./data/geo
COPY --from=builder /src/build-docker/examples/*_web_cli ./build/examples/
# 兜底：宿主机 umask/权限漂移（历史上 web/ 出现过 600 文件）不得阻塞非 root 运行时用户读取
RUN chmod -R a+rX web config data build
RUN mkdir -p /app/licenses
COPY --from=builder /src/3rdparty/swisseph/LICENSE ./licenses/SWISSEPH-LICENSE
RUN mkdir -p /app/.zhouyilab \
    && chown -R zhouyi:zhouyi /app

USER zhouyi
EXPOSE 8768
VOLUME ["/app/.zhouyilab"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8768/api/v1/health', timeout=3)"

CMD ["python3", "web/server.py", "--port", "8768"]
