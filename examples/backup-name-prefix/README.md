# Put a literal prefix in a Backuper filename

For a filename stem such as `mcl4d2_2026-10-21_17-00-10`, use:

```yaml
backup:
  backupFileNameFormat: "'mcl4d2_'yyyy-MM-dd_HH-mm-ss"
```

Change the existing field in your configuration, keeping its indentation and all other settings. This is a snippet, **not a replacement for the whole file**. Backuper 4.1.2 puts the field under `backup`; if an older version uses a different layout, keep that version's existing location.

There are two quote layers:

- The outer double quotes belong to YAML and surround the whole value.
- The inner single quotes reach Java's date formatter and make `mcl4d2_` literal text.

The value received by Java is `'mcl4d2_'yyyy-MM-dd_HH-mm-ss`. Without the inner quotes, letters in the prefix are interpreted as date-pattern letters. The original form `'mcl4d2_'yyyy-MM-dd_HH-mm-ss"` also closes the YAML string before the date pattern, making the YAML invalid.

Keep the full date **and time** portion: [Backuper 4.1.2 validates the pattern](https://github.com/DVDishka/Backuper/blob/4.1.2/src/main/java/ru/dvdishka/backuper/backend/config/BackupConfig.java) by formatting a date/time and parsing it back into `LocalDateTime`. A literal-only prefix is insufficient. Its [configuration guide](https://github.com/DVDishka/Backuper/blob/master/wiki/Configuration.md) describes the field; [Java's formatter reference](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/time/format/DateTimeFormatter.html) explains literal quotes.

After editing, use your normal configuration reload or server restart and check the next backup's name. If it still resets, the plugin version and configuration-loading error would help distinguish another invalid field from this quoting issue. Keep a copy of your configuration before editing it.

## Run the local example

This check needs a JDK 21 or newer and SnakeYAML 2.6 from Maven Central. From this directory:

```sh
curl -fL -o snakeyaml-2.6.jar https://repo.maven.apache.org/maven2/org/yaml/snakeyaml/2.6/snakeyaml-2.6.jar
java -cp snakeyaml-2.6.jar CheckFormat.java example.yml
```

The JAR's SHA-256 is `c8f7a98e7394adda02f6317249710e4d1b4c7a25aa8c7eace0c2eea52eb8bf85`.

Expected output:

```text
mcl4d2_2026-10-21_17-00-10
Date/time parsed back; two YAML save/reload cycles preserved all values; input unchanged.
```

The check is specific to this example and expected filename. It parses the YAML, uses the same JDK formatter operations as the plugin, and saves/reloads a temporary copy twice. It preserves parsed values, not comment formatting, and leaves the input untouched. Checked with JDK 21.0.12.1 and SnakeYAML 2.6; malformed YAML and an unquoted Java prefix fail. The complete Paper/Folia server, backup creation and the requester's installation were not run.

## Optional coffee

This example is free. If it saved you some time and you'd like to buy me a coffee, a small contribution is welcome, but never expected.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
