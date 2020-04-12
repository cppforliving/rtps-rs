#!/bin/bash
grep -Po '(?<= )[[:alnum:]\-_]*?(?=\=")' dds_rtps_uml_xmi.xmi | sort | uniq > xmi_attrs.txt
grep -Po '(?<=[^</])uml:[[:alnum:]:\-_]*' dds_rtps_uml_xmi.xmi | sort | uniq > xmi_types.txt
grep -Po '(?<=[</])[[:alnum:]:\-_]*(?=[ >])' dds_rtps_uml_xmi.xmi | sort | uniq > xmi_tags.txt
