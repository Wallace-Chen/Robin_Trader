from utilities import marketTime
import os
import psutil


pidfile = "/var/run/ibot.pid"
mytime = marketTime("", False)
if(mytime.opennow()): market = "Open"
else: market = "Closed"
iBot = "Off"
if os.path.isfile(pidfile):
    with open(pidfile,"r") as f:
        pid = int(f.read())
    if psutil.pid_exists(pid):
        iBot = "On"

status = "/var/www/html/test/data/status.txt"
with open(status, "w") as f:
    f.write(market+"\n")
    f.write(iBot)
