#!/bin/bash

python ../../networking.py ../../calpoly.ini &
sleep 3
./test_ms_1 gthrt 32 127.0.0.1 5654 127.0.0.1 19200 Armstrong5ever &
sleep 10
exit