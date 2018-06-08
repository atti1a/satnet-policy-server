# Mission Description

A mission is described by the `Mission` class, which is modeled of the
`satellite_info` structure from the SatComm LCM-generated files.

```c
struct satellite_info {
    string name;
    string description;
    string tleUrl;
    string tleName;
    int32_t kissTcpPort;
    string ax25_callsign;
    int8_t ax25_ssid;
    int32_t ip_addr;
    string l2_header_type;
    string l3_header_type;
    set_rf_params rxParams;
    set_rf_params txParams;
    int32_t tracking_priority;
    string mission_server;
    int32_t mission_server_port;
    boolean tracking;
    tle_track_params tle;
}

struct set_rf_params {
    int8_t     use_for_tx;
    int8_t     use_for_rx;
    int16_t    mode;
    int32_t    baudrate;
    char*      modulation;
    char*      encoding;
    int32_t    frequency;
    double     rf_h_val;
    int32_t    fec;
    int16_t    l1_framing;
    int16_t    l1_checksum;
};

struct tle_track_params {
    char*      name;
    char*      tle_line1;
    char*      tle_line2;
    int32_t    track_offset;
};
```
