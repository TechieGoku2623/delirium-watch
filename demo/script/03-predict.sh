#!/usr/bin/env bash
set +e
delirium-watch predict --patient P001 --horizon 12 --explain
exit $?
