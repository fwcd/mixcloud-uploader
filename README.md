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

For a more detailed overview of the available flags, invoke

```sh
mixcloud-uploader --help
```

### Presets

If you upload mixes regularly with a mostly fixed naming scheme, having to specify the upload parameters every time can become verbose. For this reason, this tool supports _presets_, which can be defined in `~/.config/mixcloud-uploader/config.json`, e.g. like this:

```json
{
  "presets": {
    "pop": {
      "name": "My Pop Mix No. (\\d+)",
      "artwork": "path/to/some/artwork.png",
      "tags": ["pop"]
    }
  }
}
```

When invoked as follows, the tool will then query the existing uploads to find a name with an autoincremented mix number and use the remaining parameters from the preset:

```sh
mixcloud-uploader --preset pop
```

### JSON Schemas

There are JSON schemas available for the configuration files, which can be added to your VSCode settings as follows:

```json
{
  "json.schemas": [
    {
      "fileMatch": [".config/mixcloud-uploader/config.json"],
      "url": "https://raw.githubusercontent.com/fwcd/mixcloud-uploader/main/config.schema.json"
    },
    {
      "fileMatch": [".config/mixcloud-uploader/auth.json"],
      "url": "https://raw.githubusercontent.com/fwcd/mixcloud-uploader/main/auth.schema.json"
    }
  ]
}
```

Adding these schemas lets VSCode provide code completion and linting in these configuration files.
