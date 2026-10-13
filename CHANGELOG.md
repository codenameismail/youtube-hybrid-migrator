# Changelog

## 2.0.0

### Fixed
- **Playlists no longer all land in YouTube Music.** YouTube-type playlists are now created through the official YouTube API, so they stay on YouTube. Music playlists are still created through YouTube Music. A MUSIC/YOUTUBE guess per playlist is written to `state/playlist_types.txt` for review.
- Subscriptions now have their own memory file, so reruns skip everything already done (YouTube Music can't list non-music channels).
- Large playlists are added in batches of 50, and one failed batch no longer loses the rest.
- Playlists keep their original **privacy and description**.
- The login token refreshes silently instead of reopening the browser each time.
- A failed read of the old account's likes now raises an error instead of quietly migrating only part of them.

### Added
- One entry point, `migrate.py`, with `likes`, `subs`, `playlists` and `reset` commands, plus `--only`, `--auto` and `--yes`.
- Account confirmation before any write, and a warning when the cookie account and the API login differ.
- Persistent daily quota tracking (`state/quota.json`) with a quota estimate before starting and a clean stop and resume.
- Replacement of YouTube-only playlists that were created the old way, with confirmation.
- Offline test suite (`python -m unittest discover -s tests`).
- `requirements.txt`, `.gitignore`, and the `docs/` folder.

### Changed
- Credentials and tokens live in `secrets/`, progress files in `state/` (both git-ignored). Tokens are now JSON instead of pickle files, so you'll log in once more.
- `transfer_master.py` and `fix_playlists.py` are replaced by `migrate.py`.
- `IMPORTANT.txt` is removed. It held personal details that don't belong in a repository; its useful content is in `docs/SETUP.md`.

### Upgrading from 1.x
Delete `transfer_master.py`, `fix_playlists.py`, `IMPORTANT.txt` and any `token_*.pickle`. Move `migrated_*.txt` and `playlist_types.txt` into `state/`, and `client_secret.json` and `new_headers.json` into `secrets/`.

## 1.0.0
- Initial hybrid migrator for likes, subscriptions and playlists.
