FROM mariadb:10.6

RUN apt-get update \
    && apt-get install -y --no-install-recommends redis-tools gzip procps \
    && rm -rf /var/lib/apt/lists/*

COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

ENTRYPOINT ["/scripts/entrypoint.sh"]
