# TR-181 Device.QoS — How It Works

## References

- [Broadband Forum TR-181 Data Model](https://device-data-model.broadband-forum.org/)
- [prpl Foundation tr181-qos plugin (GitLab)](https://gitlab.com/prpl-foundation/components/core/plugins/tr181-qos)
- [prplOS QoS Documentation](https://prpl-foundation.gitlab.io/prplos/feeds/feed-prpl/QoS..html)
- [BBF cwmp-data-models QoS XML](https://github.com/BroadbandForum/cwmp-data-models/blob/master/tr-181-2-18-1-qos.xml)

## Overview

The TR-181 `Device.QoS` object models packet classification and queueing behavior.
In these dumps, the most useful operational view is the mapping between:

- `Classification.{i}` rules
- `Queue.{i}` instances
- `Shaper.{i}` instances

## Object Hierarchy

```
Device.QoS
├── Classification.{i}
├── Queue.{i}
└── Shaper.{i}
```

## What The Visualizer Shows

The visualizer focuses on the operational core:

- classifications with order, protocol, address filters, direction, and traffic class
- queues with interface, precedence, scheduler, shaping rate, and traffic classes
- shapers with interface, shaping rate, and burst size

It tries to connect classifications to queues through `TrafficClass` and `Queue.TrafficClasses`.
It intentionally excludes queue stats, policers, and the full classifier subtree in v1.

## Reading the Output

The script prints:

1. an overview box with counts
2. a classifications section
3. a queues section
4. a shapers section
5. a queue summary table

The layout adapts to terminal width:

- **≥ 90 columns**: aligned classification, queue, and shaper tables
- **< 90 columns**: compact stacked summaries
