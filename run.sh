#!/bin/bash

cd /home/mekku/Documents/set-dashboard
source .env/bin/activate
export DISPLAY=:0
python web.py  2>&1 > /dev/null &
export APP_PID=$!

#sleep 5

#chromium-browser --kiosk --app='http://127.0.0.1:5000' --disable-session-crashed-bubble --disable-infobars
# chromium-browser --kiosk --app='http://127.0.0.1:5000' --incognito --disable-session-crashed-bubble --disable-infobars

#kill $APP_PID
