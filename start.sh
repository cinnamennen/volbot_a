#!/bin/bash
python setup.py install
screen -S volbot -m volbot chat.freenode.net '#volchat' $1 $2
