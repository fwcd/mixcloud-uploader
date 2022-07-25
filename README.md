# Mixcloud Uploader

[![Typecheck](https://github.com/fwcd/mixcloud-uploader/actions/workflows/typecheck.yml/badge.svg)](https://github.com/fwcd/mixcloud-uploader/actions/workflows/typecheck.yml)

A small tool for uploading [Mixxx](https://www.mixxx.org) recordings to [Mixcloud](https://www.mixcloud.com), along with tracklists and optional artwork.

## Usage

To use the tool, first obtain a client id and secret by [registering an API application](https://www.mixcloud.com/developers/create/). You can either pass these credentials as parameters (`--client-id` and `--client-secret`) or, more conveniently, create a file at `~/.config/mixcloud-uploader/auth.json`:

```json
{
  "client-id": "YOUR_CLIENT_ID",
  "client-secret": "YOUR_CLIENT_SECRET"
}
```

To upload the latest mix from your `~/Music/Mixxx/Recordings` (customizable via `--recordings-dir`), just run

```sh
mixcloud-uploader --name YOUR_MIX_NAME
```

To choose a custom recording, make sure that `YOUR_RECORDING_NAME.wav` and `YOUR_RECORDING_NAME.cue` are located in the aforementioned directory and pass

```sh
mixcloud-uploader --name YOUR_MIX_NAME --recording-name YOUR_RECORDING_NAME
```
