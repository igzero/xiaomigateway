# xiaomigateway
The HomeAssiatant custom component. Uses python-miio package ( Vers.  >= 0.3.7 ) (https://github.com/rytilahti/python-miio/).
Allows you to manage the following devices connected to the XiaomiGateway:
- Lamp "Aqara LED Light Bulb (ZNLDP12LM)". Identifier in "MiHome": 'lumi.light.aqcn02'.
  Supports brightness and color temperature control.
- Two-channel relay "Aqara (LLRZMK11LM)". The identifier in "MiHome" is 'lumi.relay.c2acn01'.
  Support: Control channel_1 and channel_2, CURRENT_POWER, POWER_CONSUMED
- XiaomiGateway FM Radio.
  Support: Turn on/off, sound control (including MUTE), next station, previous station,
  flexible setting of stations, including favorites from "MiHome", select stations from the list.
  Because in the new version of firmware not working the command 
  '"method":'play_specify_fm' "params": {"id": xxx,"type": 0,"url":"http://your_arbitrary_link/file.m3u8"'
  The command is perceived, but the stream is not played. This capability is left, but performance is not guaranteed.


To enable "xiaomigateway" in your installation, the following instruction must be followed:
1. Patch the python-miio (file device.py).

   cd /path_to_python-miio_dir
   
   patch -p1 < device.py.patch

   This is path for python-miio library,  parameter "sid" was added to give the \"sid\"-s of the children devices connected
   to the Xiaomi Gateway.   
2. Copy directory "xiaomigateway" to you custom_component directory
3. Add to your configuration.yaml file:

== configuration.yaml ==

xiaomigateway:

    host: 192.168.0.1
    token: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    
    light:
      - sid: lumi.158d0003e99991
        name: LightName
        
    switch:
      - sid: lumi.158d0003c99991
        name: RelayName
        
    media_player:
        name: FmRadioName
        source_list: [
                Ретро FM,
                Детское радио,
                Дорожное радио,
                Радио Energy,
                Европа Плюс,
                Авторадио
            ]
        program_list: [
                [527782001],
                [527782002],
                [527782003],
                [527782004],
                [527782005],
                [1023,"http:\/\/192.168.0.254\/527782006.m3u8"]
            ]
            
== End configuration.yaml ==

CONFIGURATION VARIABLES


host
    (string) (Required)
    The host/IP address the of gateway.
    
token
    (string) (Required)
    The API token of your XiaomiGateway
    
light
    (map) (Optional)
    A list of lights to set up.

    sid
        (string)(Required)
        The SID your Aqara LED Light Bulb.
        SIDs can be used without the suffix "lumi."
        For example, "lumi.1234567890xxx" can be written as "123456789xxx"
    name
        (string)(Optional)
        The Name your Aqara LED Light Bulb
        
switch
    (map) (Optional)
    A list of relays to set up.

    sid
        (string)(Required)
        The SID your Aqara Relay.
        SIDs can be used without the suffix "lumi."
        For example, "lumi.1234567890xxx" can be written as "123456789xxx"
    name
        (string)(Optional)
        The Name your Aqara Relay.
        
media_player
    (map) (Optional)
    Only element the XiaomiGateway FM Radio player.

    name
        (string)(Optional)
        The Name your FM Radio XiaomiGateway.
    source_list
        (list)(Required)
        Ordered list of Name your stantion.
        Each element of the list has type (string).
        List can be empty.
    program_list
        (list)(Required)
        List of broadcast source elements of radio stations. Each item in the list is of type (list).
        List cannot be empty
        The data format of each elment is list [ID, URL].
            ID
                (positive int)(Required)
                internal XiaomiGateway station ID, positive_int type.
                If this ID is from the list of favorite stations, the URL is not specified.
            URL
                (url)(Optional)
                link to the broadcast stream of the radio station in M3U8 format.
                Has the URL type.

(C) 2020 Igor A. Putintsev  ig.zero@rambler.ru
