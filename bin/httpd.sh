#!/bin/bash -x

cd "$(dirname "${BASH_SOURCE[0]}")/../www/"
exec twistd -n web --path .
