#!/bin/awk -f

function export(values, name) {
  if (values["metric_count"] < 1) {
    return
  }
  delete values["metric_count"]

  printf("# HELP %s%s %s sensor reading from freeipmi\n", namespace, name, help[name]);
  printf("# TYPE %s%s gauge\n", namespace, name);
  for (sensor in values) {
    printf("%s%s{sensor=\"%s\"} %f\n", namespace, name, sensor, values[sensor]);
  }
}

# Fields are Bar separated, with space padding.
BEGIN {
  FS = "[ ]*[|][ ]*";
  namespace = "node_ipmi_";

  # Friendly description of the type of sensor for HELP.
  help["temperature_celsius"] = "Temperature";
  help["volts"] = "Voltage";
  help["amperes"] = "Current";
  help["power_watts"] = "Power";
  help["speed_rpm"] = "Fan";
  help["status"] = "Chassis status";

  temperature_celsius["metric_count"] = 0;
  volts["metric_count"] = 0;
  amperes["metric_count"] = 0;
  power_watts["metric_count"] = 0;
  speed_rpm["metric_count"] = 0;
  status["metric_count"] = 0;
}

# Not a valid line.
{
  if (NF < 3) {
    next
  }
}

# $4 is value field.
$4 ~ /N\/A/ {
  next
}

# $5 is units field.
$5 ~ /C/ {
  temperature_celsius[$2] = $4;
  temperature_celsius["metric_count"]++;
}

$5 ~ /V/ {
  volts[$2] = $4;
  volts["metric_count"]++;
}

$5 ~ /A/ {
  amperes[$2] = $4;
  amperes["metric_count"]++;
}

$5 ~ /W/ {
  power_watts[$2] = $4;
  power_watts["metric_count"]++;
}

$5 ~ /RPM/ {
  speed_rpm[$2] = $4;
  speed_rpm["metric_count"]++;
}

$2 ~ /Chassis/ {
  status[$2] = sprintf("%d", substr($4,3,2));
  status["metric_count"]++;
}

END {
  export(temperature_celsius, "temperature_celsius");
  export(volts, "volts");
  export(amperes, "amperes");
  export(power_watts, "power_watts");
  export(speed_rpm, "speed_rpm");
  export(status, "status");
}
