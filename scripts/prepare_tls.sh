#!/bin/bash
#
# Copyright 2026 Enactic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Generate a self-signed certificate for the local HTTPS reverse proxy
# (the "https" compose service), which WebXR testing needs because WebXR
# only runs in a secure context. Use a host name that the VR device can
# resolve, such as the .local name configured automatically by Avahi:
#
#   scripts/prepare_tls.sh $(hostname).local
#
# This is the same scheme as dora-openarm-webxr's example/prepare_tls.sh.

set -eu

if [ $# -ne 1 ]; then
  echo "Usage: $0 SERVER_NAME"
  echo " e.g.: $0 $(hostname).local"
  exit 1
fi

server_name=$1
root_name="${server_name}"

if [ "$(uname)" = "Darwin" ]; then
  PATH="$(brew --prefix openssl@3)/bin:${PATH}"
  extfile="$(brew --prefix)/etc/openssl@3/openssl.cnf"
else
  extfile=/etc/ssl/openssl.cnf
fi

cd "$(dirname $0)/../https"

openssl req \
  -addext "subjectAltName = DNS:${root_name}" \
  -keyout root.key \
  -new \
  -nodes \
  -out root.csr \
  -subj "/CN=${root_name}" \
  -text
chmod go-rwx root.key

openssl x509 \
  -copy_extensions copy \
  -days 3650 \
  -extensions v3_ca \
  -extfile ${extfile} \
  -in root.csr \
  -out root.crt \
  -req \
  -signkey root.key \
  -text

openssl req \
  -addext "subjectAltName = DNS:${server_name}" \
  -keyout server.key \
  -new \
  -nodes \
  -out server.csr \
  -subj "/CN=${server_name}" \
  -text
chmod og-rwx server.key

openssl x509 \
  -CA root.crt \
  -CAcreateserial \
  -CAkey root.key \
  -copy_extensions copy \
  -days 365 \
  -in server.csr \
  -out server.crt \
  -req \
  -text
