#!/bin/bash

while true
do
sleep 5
echo "Hello, I am now going to run massActualCSVImport.py - `date`"
python /app/massActualCSVImport.py
echo "Hello, I have finished running massActualCSVImport.py - `date`"
echo "sleeping for 680 seconds, night night - `date`"
sleep 680
echo "waking up - `date`"
done
