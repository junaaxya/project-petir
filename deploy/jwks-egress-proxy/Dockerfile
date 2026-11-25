FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates squid \
    && apt-get clean \
    && find /var/lib/apt/lists -mindepth 1 -delete

COPY deploy/jwks-egress-proxy/entrypoint.sh /usr/local/bin/jwks-proxy-entrypoint
RUN chmod 0555 /usr/local/bin/jwks-proxy-entrypoint

USER proxy
EXPOSE 3128
ENTRYPOINT ["/usr/local/bin/jwks-proxy-entrypoint"]
