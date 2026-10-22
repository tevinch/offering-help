import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;
import org.yaml.snakeyaml.LoaderOptions;
import org.yaml.snakeyaml.Yaml;
import org.yaml.snakeyaml.constructor.SafeConstructor;

/** Checks a configuration copy; does not load a server or make a backup. */
class CheckFormat {
    private static final LocalDateTime SAMPLE = LocalDateTime.of(2026, 10, 21, 17, 0, 10);
    private static final String EXPECTED = "mcl4d2_2026-10-21_17-00-10";

    public static void main(String[] args) throws Exception {
        Path source = Path.of(args.length == 0 ? "example.yml" : args[0]);
        byte[] original = Files.readAllBytes(source);
        LoaderOptions options = new LoaderOptions();
        options.setAllowDuplicateKeys(false);
        Yaml yaml = new Yaml(new SafeConstructor(options));
        Object loaded = yaml.load(new String(original, java.nio.charset.StandardCharsets.UTF_8));
        check(loaded);
        Path copy = Files.createTempFile("filename-format-", ".yml");
        try {
            for (int i = 0; i < 2; i++) {
                Files.writeString(copy, yaml.dump(loaded));
                Object reloaded = yaml.load(Files.readString(copy));
                if (!loaded.equals(reloaded)) throw new AssertionError("Settings changed on round trip");
                check(reloaded);
                loaded = reloaded;
            }
        } finally {
            Files.deleteIfExists(copy);
        }
        if (!java.util.Arrays.equals(original, Files.readAllBytes(source))) {
            throw new AssertionError("Input file changed");
        }
        System.out.println(EXPECTED);
        System.out.println("Date/time parsed back; two YAML save/reload cycles preserved all values; input unchanged.");
    }

    private static void check(Object document) {
        if (!(document instanceof Map<?, ?> root)
                || !(root.get("backup") instanceof Map<?, ?> backup)
                || !(backup.get("backupFileNameFormat") instanceof String pattern)) {
            throw new IllegalArgumentException("Expected backup.backupFileNameFormat as a string");
        }
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern(pattern);
        String name = SAMPLE.format(formatter);
        if (!EXPECTED.equals(name)) throw new AssertionError("Unexpected filename: " + name);
        if (!SAMPLE.equals(LocalDateTime.parse(name, formatter))) {
            throw new AssertionError("Date/time did not parse back");
        }
    }
}
