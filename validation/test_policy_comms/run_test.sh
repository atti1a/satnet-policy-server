#!/bin/bash

python ../../networking.py ../../calpoly.ini &
sleep 3
python ../../networking.py ../../purdue.ini &
sleep 10
exit