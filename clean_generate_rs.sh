#!/bin/bash
set -x
rm -r src/Protocol/ src/Profile_for_DDS__Protocol1/ uml/ xmi:XMI/
python generate_rs.py
cargo fmt
find src/Protocol/ src/Profile_for_DDS__Protocol1/ uml/ xmi:XMI/ | sort
