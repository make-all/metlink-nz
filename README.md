# Metlink Wellington Transport for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

This is a custom component for Home Assistant which uses
the [Metlink opendata API](https://opendata.metlink.org.nz/) to obtain
realtime departure info for Greater Wellington public transport, which can
then be displayed on your Home Assistant dashboard or used in automations.


## Installation

The integration can be installed by adding the custom repository
https://github.com/make-all/metlink-nz to HACS, and installing from there.
If you prefer to instal manually, copy `custom_components/metlink` to your
installation's `config/custom_components` directory.

### Configuration

After installing the custom component, you still need to configure it before
it will do anything.

The integration can be added from the Integrations configuration screen.

API keys can be obtained by registering on the
[Metlink Developer Portal](https://opendata.metlink.org.nz/).

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


`stop_id` for Train and Cable Car stops is a 4 character alphabetic
code, and for bus and ferry stops, is a 4 digit numeric code.
The IDs are on bus stop signs, or can be looked up on the
[Metlink](https://metlink.org.nz) main web site.


If your stop is busy with multiple routes, you can filter by route and/or destination.  Currently exact matches are expected and only a single route or destination can be specified, though the destination does check the name as well as the stop id for a match, though some of the names that come through the API are abbreviated in ways that do not match the main web site so stop id will be more reliable.  The destination filter is only available on the final destination, not any intermediate stops.


Each stop will create a sensor in Home Assistant, which will return the next departure time as its status.

It will also return attributes for departure time, service, service
name, destination name, stop id for the destination, and status.  The
duplication of departure time in the attributes makes more sense when
there is more than one result being returned.

If more than 1 result is requested in `num_departures`, the attributes
will be suffixed with a number for second and subsequent departures.
