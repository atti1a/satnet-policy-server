#!/bin/bash

python ../../networking.py ../../calpoly.ini &
sleep 3
python ../../networking.py ../../purdue.ini &
sleep 3
./test_ms_1 test_ms_1 33 127.0.0.1 5654 127.0.0.1 19200 Armstrong5ever &
./test_ms_2 test_ms_2 43 127.0.0.1 5655 127.0.0.1 19200 Armstrong5ever &

exit