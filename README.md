# HA-Component-mythtv-frontend
Home Assistant media player component for MythTV 0.27+ Frontend

## About This Component
This component is being developed to allow Home Assistant to interact with a MythTV frontend using the MythTV API Service (available in MythTV version 0.27 and later).  It will work with a frontend-only or combination frontend and backend machine.  This component will only add frontend services; a future component may be developed to provide interfaces with the backend.

This component is a media_player entity, and therefore will try to implement as many of the media_player funcitons including play/pause, volume control, and chapter controls.

## Getting Started

### Prerequisites
[Home Assistant](https://home-assistant.io) installed and operational.  Installation using a [VirtualEnv](https://home-assistant.io/docs/installation/virtualenv/) or [Hassbian](https://home-assistant.io/docs/hassbian/installation/) on Raspberry Pi is recommended and installation instructions are based on this method.

[MythTVServicesAPI Utilities](https://github.com/billmeek/MythTVServicesAPI) 

### Installing MythTVServicesAPI
Add MythTVServicesAPI to your Python3.5/site-packages folder - ```/srv/homeassistant/lib/python3.5/site-packages``` if using VirtualEnv or Hassbian, by performing the following commands:
```
sudo su -s /bin/bash homeassistant
source /srv/homeassistant/bin/activate
cd /srv/homeassistant/lib/python3.5/site-packages
git clone https://github.com/billmeek/MythTVServicesAPI
```
If not using VirtualEnv/Hassbian, use ```git clone https://github.com/billmeek/MythTVServicesAPI``` in your Python installation's site-packages folder.

### Installing mythfrontend.py custom component
In the Home Assistant configuration directory (located at ```/home/homeassistant/.homeassistant``` for VirtualEnv/Hassbian installs), make sure ```/custom_components/media_player``` exists.  If it does not exist, perform the following:
```
cd /home/homeassistant/.homeassistant  #Or your configuration directory
mkdir custom_components
cd custom_components
mkdir media_player
cd media_player
```
Copy the ```mythfrontend.py``` file from this repository to the new media_player folder.

## Adding and Configuring a MythTV Frontend in Home Assistant

### Basic Configuration
In your ```configuration.yaml``` file, add the following:
```
media_player:
  - platform: mythfrontend
    host: (hostname or IP address)
```
Note - if using IPv6, use the format ```"[::]"``` replacing ```::``` with your full IPv6 address.  ```host``` also takes hostnames if they can be resolved by DNS.

### Optional Configuration Items
```
media_player:
  - platform: mythfrontend
    host: (hostname or IP address)
    name: Friendly frontend name (default: MythTV Frontend)
    port: Frontend API services port (default: 6547)
```

## NOTES

* MythTV Services API in versions 0.28 and 0.29-pre appear to have broken implementations of SendAction, so these versions may not respond correctly to frontend actions.  0.27 should work but has not yet been tested.

## Acknowledgements

* [MythTVServicesAPI](http://github.com/billmeek/MythTVServicesAPI) - Implementing an easy way to interface with MythTV
* [MythTV Wiki - Services API](https://www.mythtv.org/wiki/Services_API) - Examples and descriptions of MythTV Services API
* Based off existing samsungtv and anthemav components
