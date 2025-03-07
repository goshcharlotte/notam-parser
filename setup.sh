#! /bin/bash

echo installing python libraries
/usr/bin/pip3 install -r requirements.txt

# check for docker config and data volumes and create them if they don't exist
if docker volume inspect notam-data 2>&1 | grep -q 'no such volume' ; then
  echo notam-data volume not present, creating
  docker volume create notam-data &> /dev/null
  echo notam-data volume created
fi

if docker volume inspect notam-config 2>&1 | grep -q 'no such volume' ; then
  echo notam-config volume not present, creating
  docker volume create notam-config &> /dev/null
  echo notam-config volume created
fi

# set up cron job to run scheduler script
if crontab -l | grep -q "notam-scheduler.sh" ; then
    echo cron job found, skipping add
else
	echo no existing cron job found, adding
    CWD=`pwd`
    SCHEDULER=`echo $CWD/notam-scheduler.sh`
    LOGFILE=`echo $CWD/notam-cron.log`
    (crontab -l ; echo "1 * * * * $SCHEDULER >> $LOGFILE 2>&1") | crontab -
    echo cron job added
fi
