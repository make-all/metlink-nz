# Metlink Wellington Transport for Home Assistant

This is a custom component for Home Assistant which uses
the [Metlink opendata API](https://opendata.metlink.org.nz/) to obtain
realtime departure info for Greater Wellington public transport, which can
then be displayed on your Home Assistant dashboard or used in automations.

[![BuyMeCoffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/jasonrumney)

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
[Metlink Developer Portal](https://opendata.metlink.org.nz/).  **Be sure to subscribe to the "Metlink Open Data API".** Currently this is the only API they offer, and is free, but is still unsubscribed by default.


`stop_id` for Train and Cable Car stops is a 3 to 4 character alphabetic
code, and for bus and ferry stops, is a 4 digit numeric code.
The IDs are on bus stop signs, or can be looked up on the
[Metlink](https://metlink.org.nz) main web site.


If your stop is busy with multiple routes, you can filter by route and/or destination.  Currently exact matches are expected and only a single route or destination can be specified, though the destination does check the name as well as the stop id for a match, but some of the names that come through the API are abbreviated in ways that do not match the main web site so stop id will be more reliable.  The destination filter is only available on the final destination, not any intermediate stops.


Each stop will create a sensor in Home Assistant, which will return the next departure time as its status.

It will also return attributes for departure time, service, service
name, destination name, stop id for the destination, status, service alerts
and more.  The duplication of departure time in the attributes makes more
sense when there is more than one result being returned.

If more than 1 result is requested in `num_departures`, the attributes
will be suffixed with a number for second and subsequent departures.

Stop IDs sometimes behave differently, E.g. if your start stop ID is NAEN and the final destination is WELL, it doesn't work but it works with WELL1 as the final destination. To ensure that you have the correct final destination Stop ID, create a sensor without a final destination and get the final destination which shows up in the attributes.

# Acknowledgements

Thanks to Greater Wellington Regional Council for making their data available
via an open API, and the following users who have submitted improvements to
this Home Assistant integration.

- [messum](https://github.com/messum) for identifying that train stations are not always 4 characters, and fixing that, and contributing documentation to advise on the new train station naming complexity where major stations have numbered source/destination ids.
- [Me-sudoer](https://github.com/Me-sudoer) for finding an issue with the HA iOS app's different handling of timestamps than web and Android.
- [meringu](https://github.com/meringu) for contributing service alert support.
