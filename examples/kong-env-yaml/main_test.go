package main

import (
	"bytes"
	"encoding/json"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestCLIOutput(t *testing.T) {
	clearEnv(t)
	file := configFile(t, "debug: true\nworkers: 8\nname: from-yaml\ntimeout: 30s\ntags: [yaml, shared]\nlabels: {region: yaml}\n")
	t.Setenv("DEBUG", "false")
	t.Setenv("APP_WORKERS", "0")
	t.Setenv("APP_NAME", "")
	t.Setenv("APP_TIMEOUT", "2s")
	t.Setenv("APP_TAGS", "env,shared")
	t.Setenv("APP_LABELS", "region=env;team=demo")
	for _, args := range [][]string{
		{"--config", file, "--workers=3"},
		{"--workers=3", "-c", file},
	} {
		var out bytes.Buffer
		if err := run(args, &out); err != nil {
			t.Fatal(err)
		}
		var got map[string]any
		if err := json.Unmarshal(out.Bytes(), &got); err != nil {
			t.Fatal(err)
		}
		want := map[string]any{
			"debug": false, "workers": float64(3), "name": "", "timeout": "2s",
			"tags": []any{"env", "shared"}, "labels": map[string]any{"region": "env", "team": "demo"},
		}
		if !reflect.DeepEqual(got, want) {
			t.Fatalf("args %v: got %s", args, out.String())
		}
	}
}

func TestCLIDefaultsAndYAML(t *testing.T) {
	clearEnv(t)
	for _, tc := range []struct {
		name string
		args []string
		want string
	}{
		{"defaults", nil, `{"debug":false,"workers":2,"name":"local","timeout":"5s","tags":["base"],"labels":{"region":"local"}}`},
		{"yaml", []string{"-c", configFile(t, "debug: true\nworkers: 8\n")}, `{"debug":true,"workers":8,"name":"local","timeout":"5s","tags":["base"],"labels":{"region":"local"}}`},
	} {
		t.Run(tc.name, func(t *testing.T) {
			var out bytes.Buffer
			if err := run(tc.args, &out); err != nil {
				t.Fatal(err)
			}
			if strings.TrimSpace(out.String()) != tc.want {
				t.Fatalf("got %s; want %s", out.String(), tc.want)
			}
		})
	}
}

func TestErrorsDoNotPrintSettings(t *testing.T) {
	cases := []struct {
		name, body, envName, envValue string
		args                          []string
		want                          string
	}{
		{name: "malformed_yaml", body: "debug: [", want: "YAML config decode error"},
		{name: "invalid_yaml_bool", body: "debug: not-a-bool\n", want: "--debug"},
		{name: "invalid_yaml_int", body: "workers: many\n", want: "--workers"},
		{name: "invalid_yaml_duration", body: "timeout: tomorrow\n", want: "--timeout"},
		{name: "invalid_env_bool", body: "debug: true\n", envName: "DEBUG", envValue: "invalid", want: "from envar DEBUG"},
		{name: "empty_env_bool", body: "debug: true\n", envName: "DEBUG", envValue: "", want: "from envar DEBUG"},
		{name: "invalid_env_int", body: "workers: 8\n", envName: "APP_WORKERS", envValue: "many", want: "from envar APP_WORKERS"},
		{name: "empty_env_int", body: "workers: 8\n", envName: "APP_WORKERS", envValue: "", want: "from envar APP_WORKERS"},
		{name: "invalid_env_duration", body: "timeout: 30s\n", envName: "APP_TIMEOUT", envValue: "tomorrow", want: "from envar APP_TIMEOUT"},
		{name: "cli_does_not_rescue_invalid_env", body: "debug: true\n", envName: "DEBUG", envValue: "invalid", args: []string{"--debug=false"}, want: "from envar DEBUG"},
		{name: "invalid_cli", body: "workers: 8\n", args: []string{"--workers=many"}, want: "--workers"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			clearEnv(t)
			if tc.envName != "" {
				t.Setenv(tc.envName, tc.envValue)
			}
			args := append([]string{"--config", configFile(t, tc.body)}, tc.args...)
			var out bytes.Buffer
			err := run(args, &out)
			if err == nil || !strings.Contains(err.Error(), tc.want) {
				t.Fatalf("error %v; want %q", err, tc.want)
			}
			if out.Len() != 0 {
				t.Fatalf("invalid input printed settings: %s", out.String())
			}
		})
	}
	t.Run("missing_selected_file", func(t *testing.T) {
		clearEnv(t)
		var out bytes.Buffer
		err := run([]string{"--config", filepath.Join(t.TempDir(), "missing.yaml")}, &out)
		if err == nil || !strings.Contains(err.Error(), "missing.yaml") {
			t.Fatalf("missing selected file: %v", err)
		}
		if out.Len() != 0 {
			t.Fatal("missing file printed settings")
		}
	})
}
