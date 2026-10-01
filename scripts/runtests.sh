#!/bin/bash
coverage erase
if [ -d "/reports" ]; then
    pytest -s --cov=abl.vpath --junit-xml=/reports/report.xml
else
    pytest -s --cov=abl.vpath
fi
