# Metroinfo Christchurch Transport for Home Assistant

This is a custom component for Home Assistant which uses
the [Metroinfo API](https://apidevelopers.metroinfo.co.nz) to obtain
realtime departure info for Greater Christchurch public transport, which can
then be displayed on your Home Assistant dashboard or used in automations.


## Installation

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

The integration can be installed using HACS.
If you prefer to instal manually, copy `custom_components/metlink` to your
installation's `config/custom_components` directory.

### Configuration

After installing the custom component, you still need to configure it before
it will do anything.

The integration can be added from the Integrations configuration screen.

API keys can be obtained by registering on the
[Metroinfo Developer Portal](https://https://apidevelopers.metroinfo.co.nz/).  Be sure to subscribe to the "Siri Realtime" for free.

If you prefer to configure using yaml instead of the UI, add something like
the following to your `config/configuration.yaml`:

```
sensor:
  - platform: metlink
    api_key: abcdefg1234xzy
    stops:
      - stop_id: 9999
      - stop_id: WELL
        route: HVL
      - stop_id: 5016
        destination: 3451
        num_departures: 3
```


`stop_id` bus stops, is a 5 digit numeric code.
The IDs are on bus stop signs, or can be looked up on the
[Metroinfo](https://metroinfo.co.nz) main web site.


If your stop is busy with multiple routes, you can filter by route and/or destination.  Currently exact matches are expected and only a single route or destination can be specified, though the destination does check the name as well as the stop id for a match, though some of the names that come through the API are abbreviated in ways that do not match the main web site so stop id will be more reliable.  The destination filter is only available on the final destination, not any intermediate stops.


Each stop will create a sensor in Home Assistant, which will return the next departure time as its status.

It will also return attributes for departure time, service, service
name, destination name, stop id for the destination, and status.  The
duplication of departure time in the attributes makes more sense when
there is more than one result being returned.

If more than 1 result is requested in `num_departures`, the attributes
will be suffixed with a number for second and subsequent departures.

