package main

import (
	"github.com/alecthomas/kong-yaml"
	"os"
	"path/filepath"
	"reflect"
	"testing"
	"time"

	"github.com/alecthomas/kong"
)

func configFile(t *testing.T, body string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "settings.yaml")
	if err := os.WriteFile(path, []byte(body), 0600); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestEnvironmentOverridesSelectedYAML(t *testing.T) {
	t.Setenv("DEBUG", "false")
	file := configFile(t, "debug: true\n")
	var cli struct {
		Config kong.ConfigFlag
		Debug  bool `default:"false" env:"DEBUG"`
	}
	parser, err := kong.New(&cli, kong.Configuration(envFirstYAML))
	if err != nil {
		t.Fatal(err)
	}
	if _, err = parser.Parse([]string{"--config", file}); err != nil {
		t.Fatal(err)
	}
	if cli.Debug {
		t.Fatal("DEBUG=false must override YAML debug:true; got true")
	}
}

func clearEnv(t *testing.T) {
	t.Helper()
	for _, name := range []string{"DEBUG", "APP_WORKERS", "APP_NAME", "APP_TIMEOUT", "APP_TAGS", "APP_LABELS", "APP_PRIMARY", "APP_SECONDARY"} {
		t.Setenv(name, "")
		if err := os.Unsetenv(name); err != nil {
			t.Fatal(err)
		}
	}
}

func TestNativeBaselineAndOriginalDoubleParse(t *testing.T) {
	clearEnv(t)
	t.Setenv("DEBUG", "false")
	file := configFile(t, "debug: true\n")
	t.Run("native_config_flag", func(t *testing.T) {
		var options cli
		parser, err := kong.New(&options, kong.Configuration(kongyaml.Loader))
		if err != nil {
			t.Fatal(err)
		}
		if _, err = parser.Parse([]string{"-c", file}); err != nil {
			t.Fatal(err)
		}
		if !options.Debug {
			t.Fatal("baseline changed: reconsider whether the wrapper is still needed")
		}
	})
	t.Run("original_double_parse", func(t *testing.T) {
		var original struct {
			Config string
			Debug  bool `default:"false" env:"DEBUG"`
		}
		first, err := kong.New(&original)
		if err != nil {
			t.Fatal(err)
		}
		if _, err = first.Parse([]string{"--config", file}); err != nil {
			t.Fatal(err)
		}
		second, err := kong.New(&original, kong.Configuration(kongyaml.Loader, original.Config))
		if err != nil {
			t.Fatal(err)
		}
		if _, err = second.Parse([]string{"--config", file}); err != nil {
			t.Fatal(err)
		}
		if !original.Debug {
			t.Fatal("baseline changed: original double parse no longer reproduces")
		}
	})
}

func TestTypedYAMLAndCLIReplacement(t *testing.T) {
	clearEnv(t)
	file := configFile(t, "debug: true\nworkers: 8\nname: from-yaml\ntimeout: 30s\ntags: [yaml, shared]\nlabels: {region: yaml, team: demo}\n")
	var options cli
	parser, err := kong.New(&options, kong.Configuration(envFirstYAML))
	if err != nil {
		t.Fatal(err)
	}
	if _, err = parser.Parse([]string{"-c", file}); err != nil {
		t.Fatal(err)
	}
	if !options.Debug || options.Workers != 8 || options.Name != "from-yaml" || options.Timeout != 30*time.Second || !reflect.DeepEqual(options.Tags, []string{"yaml", "shared"}) || !reflect.DeepEqual(options.Labels, map[string]string{"region": "yaml", "team": "demo"}) {
		t.Fatalf("YAML was not fully decoded: %+v", options)
	}
	t.Setenv("DEBUG", "true")
	t.Setenv("APP_TAGS", "env,shared")
	t.Setenv("APP_LABELS", "region=env;team=demo")
	if _, err = parser.Parse([]string{"-c", file, "--debug=false", "--tags=cli", "--labels=only=cli"}); err != nil {
		t.Fatal(err)
	}
	if options.Debug || !reflect.DeepEqual(options.Tags, []string{"cli"}) || !reflect.DeepEqual(options.Labels, map[string]string{"only": "cli"}) {
		t.Fatalf("CLI should replace env/file values: %+v", options)
	}
}

func TestConfigLayersAndRepeatedParses(t *testing.T) {
	clearEnv(t)
	first := configFile(t, "workers: 4\nname: base\n")
	second := configFile(t, "workers: 8\n")
	chosen := configFile(t, "workers: 12\nname: selected\n")
	var options cli
	parser, err := kong.New(&options, kong.Configuration(envFirstYAML, first, second))
	if err != nil {
		t.Fatal(err)
	}
	parse := func(args []string, workers int, name string) {
		t.Helper()
		if _, err := parser.Parse(args); err != nil {
			t.Fatal(err)
		}
		if options.Workers != workers || options.Name != name {
			t.Fatalf("args %v: got %+v", args, options)
		}
	}
	parse(nil, 8, "base")
	parse([]string{"-c", chosen}, 12, "selected")
	t.Setenv("APP_WORKERS", "0")
	parse([]string{"-c", chosen}, 0, "selected")
	if err := os.Unsetenv("APP_WORKERS"); err != nil {
		t.Fatal(err)
	}
	parse(nil, 8, "base") // The earlier ConfigFlag resolver must not leak.
	parse([]string{"-c", chosen, "-c", second}, 8, "base")
	parse([]string{"-c", second, "-c", chosen}, 12, "selected")
	if err := os.WriteFile(chosen, []byte("workers: 15\nname: edited\n"), 0600); err != nil {
		t.Fatal(err)
	}
	parse([]string{"-c", chosen}, 15, "edited") // Selected file reloads each parse.
	if err := os.WriteFile(second, []byte("workers: 99\n"), 0600); err != nil {
		t.Fatal(err)
	}
	parse(nil, 8, "base") // Default-path resolvers are loaded at construction.
}

func TestEmptyEnvironmentAndAliases(t *testing.T) {
	clearEnv(t)
	file := configFile(t, "name: file\n")
	var options struct {
		Config kong.ConfigFlag
		Name   string `env:"APP_PRIMARY,APP_SECONDARY" default:"default"`
	}
	parser, err := kong.New(&options, kong.Configuration(envFirstYAML))
	if err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		primary   *string
		secondary string
		want      string
	}{
		{nil, "second", "second"}, {stringPointer("first"), "second", "first"}, {stringPointer(""), "second", ""},
	} {
		if err := os.Unsetenv("APP_PRIMARY"); err != nil {
			t.Fatal(err)
		}
		if tc.primary != nil {
			t.Setenv("APP_PRIMARY", *tc.primary)
		}
		t.Setenv("APP_SECONDARY", tc.secondary)
		if _, err = parser.Parse([]string{"--config", file}); err != nil {
			t.Fatal(err)
		}
		if options.Name != tc.want {
			t.Fatalf("got %q; want %q", options.Name, tc.want)
		}
	}
}

func stringPointer(s string) *string { return &s }

func TestNestedCommand(t *testing.T) {
	clearEnv(t)
	file := configFile(t, "show:\n  name: nested-yaml\n  workers: 11\n")
	var options struct {
		Config kong.ConfigFlag
		Show   struct {
			Name    string `env:"APP_NAME" default:"default"`
			Workers int    `default:"2"`
		} `cmd:""`
	}
	t.Setenv("APP_NAME", "nested-env")
	parser, err := kong.New(&options, kong.Configuration(envFirstYAML))
	if err != nil {
		t.Fatal(err)
	}
	ctx, err := parser.Parse([]string{"--config", file, "show"})
	if err != nil {
		t.Fatal(err)
	}
	if ctx.Command() != "show" || options.Show.Name != "nested-env" || options.Show.Workers != 11 {
		t.Fatalf("nested command failed: %+v", options.Show)
	}
}
