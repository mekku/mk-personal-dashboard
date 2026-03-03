# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- **Sound notifications** on the dashboard when:
  - Bot status changes (bot comes back online after being inactive ≥ 5 min) — short beep (440 Hz)
  - A new position is opened (position count increases for a bot) — beep (554 Hz)
  - A Jenkins job completes (job was running and is now success/blue) — beep (660 Hz)
- Uses Web Audio API for in-browser beeps (no audio files required).
