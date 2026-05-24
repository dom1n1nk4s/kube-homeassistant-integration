    #! /usr/bin/bash
    scp -r ./custom_components/kube user@192.168.50.141:/DATA/AppData/homeassistant/config/custom_components/ && ssh user@192.168.50.141 "docker restart homeassistant"