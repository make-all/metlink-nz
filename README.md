# Metlink NZ Transport for Home Assistant

This repo contains a custom component for Home Assistant for interfacing
to the Metlink opendata API for obtaining realtime departure info for
Greater Wellington public transport.

## Installation
Currently this is work in progress, and it is not recommended to install it
unless you are willing to help with development.

The configuration should be something like.

```
sensor:
  - platform: metlink_nz
	api_key: <Your API key>
	stops:
	  - stop_id: <Your preferred stop>
	    route: <Optional: filter for route>
		destination: <Optional: filter for destination stop>
		num_departures: <Optional: number of departures to return, default=1>
```

API keys can be obtained by registering on the
[Metlink Developer Portal](https://opendata.metlink.org).

`stop_id` for Train and Cable Car stops is a 4 character alphabetic
code, and for bus and ferry stops, is a 4 digit numeric code.
The IDs are on bus stop signs, or can be looked up on the
[Metlink](https://metlink.org.nz) main web site.

If your stop is busy with multiple routes, you can filter by route and/or destination.  Currently exact matches are expected and only a single route or destination can be specified, though the destination does check the name as well as the stop id for a match, though some of the names that come through the API are abbreviated in ways that do not match the main web site so stop id is preferred.  The destination filter is only available on the final destination, not any intermediate stops.

Specifiying the same stop multiple times with different filters is not supported, as the stop id is used as a unique id.  You may be able to work around this by specifying the next or previous stop on the route, though the times will be off.

Each stop will create a sensor in Home Assistant, which will return the next departure time as its status.

It will also return attributes for departure time, service, service
name, destination name, stop id for the destination, and status.  The
duplication of departure time in the attributes makes more sense when
there is more than one result being returned.

If more than 1 result is requested in `num_departures`, the attributes
will be suffixed with a number.
