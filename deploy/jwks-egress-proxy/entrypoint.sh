#!/bin/sh
set -eu

domain=${ALLOWED_JWKS_HOST:-}
case "$domain" in
  https://*) domain=${domain#https://} ;;
esac
domain=${domain%/}

if ! printf '%s' "$domain" | grep -Eq '^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.cloudflareaccess\.com$'; then
  printf '%s\n' 'ALLOWED_JWKS_HOST must be one exact *.cloudflareaccess.com team hostname' >&2
  exit 64
fi

cat > /tmp/squid.conf <<EOF
acl allowed_jwks dstdomain $domain
acl tls_port port 443
acl connect_method method CONNECT
http_access allow connect_method tls_port allowed_jwks
http_access deny all
http_port 3128
cache deny all
via off
forwarded_for delete
request_header_access X-Forwarded-For deny all
access_log stdio:/dev/stdout
cache_log /dev/stderr
pid_filename /tmp/squid.pid
coredump_dir /tmp
EOF

exec squid -N -f /tmp/squid.conf
