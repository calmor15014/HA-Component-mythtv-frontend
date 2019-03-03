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

Add MythTVServicesAPI to your Python3.x/site-packages folder. If using VirtualEnv or Hassbian, switch to your homeassistant user and enter the VirtualEnv by performing the following commands:
```
sudo su -s /bin/bash homeassistant
source /srv/homeassistant/bin/activate
```
Next, install the API (check https://github.com/billmeek/MythTVServicesAPI/tree/master/dist for the latest version):
```
pip install https://raw.githubusercontent.com/billmeek/MythTVServicesAPI/master/dist/mythtv_services_api-0.1.9-py3-none-any.whl
```


### Installing mythfrontend.py custom component
In the Home Assistant configuration directory (located at ```/home/homeassistant/.homeassistant``` for VirtualEnv/Hassbian installs), make sure ```/custom_components/media_player``` exists.  If it does not exist, perform the following:
```
cd /home/homeassistant/.homeassistant  #Or your configuration directory
mkdir -p custom_components/media_player
cd custom_components/media_player
wget https://raw.githubusercontent.com/calmor15014/HA-Component-mythtv-frontend/master/mythfrontend.py
```
This makes the required custom media_player folder and copies the ```mythfrontend.py``` file from this repository to the new folder.  

## Adding and Configuring a MythTV Frontend in Home Assistant

### Basic Configuration
In your ```configuration.yaml``` file, add the following:
```
media_player:
  - platform: mythfrontend
    host: Frontend hostname or IP address
    port: Frontend API services port (optional, default: 6547)
    host_backend: Backend hostname or IP address (optional, defaults to same as host)
    port_backend: Backend API services port (optional, default: 6544)
    name: Friendly frontend name (optional, default: MythTV Frontend)
    mac: MAC address for WOL (optional)
    show_artwork: Choose whether or not to show artwork (optional, default: True)
```
Note - if using IPv6, use the format ```"[::]"``` replacing ```::``` with your full IPv6 address.  ```host``` also takes hostnames if they can be resolved by DNS.

## Notes

* MythTV Services API in version 0.29-pre appears to have a broken implementation of SendAction, so this version may not respond correctly to frontend actions.  0.28-fixes has been tested to work normally.  If the frontend status is indicated, but controls do not work, please post on the [Home Assistant development thread](https://community.home-assistant.io/t/adding-mythtv-frontend-component/16991) with your MythTV version.

## Acknowledgements

* [MythTVServicesAPI](http://github.com/billmeek/MythTVServicesAPI) - Implementing an easy way to interface with MythTV
* [MythTV Wiki - Services API](https://www.mythtv.org/wiki/Services_API) - Examples and descriptions of MythTV Services API
* Based off of existing samsungtv and anthemav components
