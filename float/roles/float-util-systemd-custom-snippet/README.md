The purpose of this role is to install a custom systemd snippet for a
given service. The following variables must be set:

`systemd_unit` is the full name of the systemd unit to customize

`fix_restart` (optional), when set to "yes" causes us to add a
"restart: always" section

`settings` (optional): a key/value dictionary containing systemd unit
settings

`tag` (optional): short identifier, the snippet will be called tag.conf
(default is "float-overrides").
