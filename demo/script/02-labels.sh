#!/usr/bin/env bash
set +e
delirium-watch labels compare --cohort data/sample/cohort.parquet
exit $?
