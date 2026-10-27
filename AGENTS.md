# Repository instructions

This repository provides `tuxbull.journal_forwarder`, a Linux Fluent Bit sender
for a Graylog GELF input. Keep the role Linux-only; Windows forwarding belongs in
the separate Winlogbeat role. Do not commit live Graylog addresses, tokens,
certificates, inventories, generated Fluent Bit state, or lab artifacts.

Validate installation, rendered Fluent Bit configuration, `fluent-bit --dry-run`,
service state, and second-run idempotency in the default disposable Linux lab.
Sender-side tests do not prove Graylog ingestion. Receiver proof requires an
approved Graylog GELF input and an exact unique marker search via the Graylog API.
For the optional k3s Event exporter bridge, prove the intended Kubernetes Event
path—not merely GELF connectivity—before describing it as verified.

`README.md` is user guidance; `CHANGELOG.md` is release history. Source
repository is `Tuxbull-Open-Source/ansible.journal_forwarder`; Galaxy FQN is
`tuxbull.journal_forwarder`. Do not self-merge. After review/merge, create an
immutable SemVer tag and published GitHub Release, then import and verify
unpinned and version-pinned Galaxy installations.
