package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"time"

	"github.com/alecthomas/kong"
)

type cli struct {
	Config  kong.ConfigFlag   `short:"c" help:"Read a YAML configuration file."`
	Debug   bool              `default:"false" env:"DEBUG" help:"Enable debug output."`
	Workers int               `default:"2" env:"APP_WORKERS" help:"Number of workers."`
	Name    string            `default:"local" env:"APP_NAME" help:"Display name."`
	Timeout time.Duration     `default:"5s" env:"APP_TIMEOUT" help:"Operation timeout."`
	Tags    []string          `default:"base" env:"APP_TAGS" help:"Comma-separated tags."`
	Labels  map[string]string `default:"region=local" env:"APP_LABELS" help:"Semicolon-separated key=value labels."`
}

func run(args []string, out io.Writer) error {
	var options cli
	parser, err := kong.New(&options,
		kong.Name("config-example"),
		kong.Description("Show settings resolved from flags, environment, YAML, and defaults."),
		kong.Writers(out, os.Stderr),
		kong.Configuration(envFirstYAML),
	)
	if err != nil {
		return err
	}
	if _, err := parser.Parse(args); err != nil {
		return err
	}
	return json.NewEncoder(out).Encode(struct {
		Debug   bool              `json:"debug"`
		Workers int               `json:"workers"`
		Name    string            `json:"name"`
		Timeout string            `json:"timeout"`
		Tags    []string          `json:"tags"`
		Labels  map[string]string `json:"labels"`
	}{options.Debug, options.Workers, options.Name, options.Timeout.String(), options.Tags, options.Labels})
}

func main() {
	if err := run(os.Args[1:], os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "config-example:", err)
		os.Exit(2)
	}
}
