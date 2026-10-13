FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
      libx11-6 libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libsm6 libice6 libgl1 libegl1 xz-utils \
    && rm -rf /var/lib/apt/lists/*
COPY blender-5.2.2-linux-x64.tar.xz /tmp/
RUN tar -xJf /tmp/blender-5.2.2-linux-x64.tar.xz -C /opt && mv /opt/blender-5.2.2-linux-x64 /opt/blender && rm /tmp/*.tar.xz
ENTRYPOINT ["/opt/blender/blender"]
