package main

import (
	"io"
	"os"

	"github.com/alecthomas/kong"
	"github.com/alecthomas/kong-yaml"
)

// envFirstYAML keeps Kong's environment values above YAML configuration.
// Register it with kong.Configuration(envFirstYAML).
func envFirstYAML(r io.Reader) (kong.Resolver, error) {
	resolver, err := kongyaml.Loader(r)
	if err != nil {
		return nil, err
	}
	return envFirstResolver{Resolver: resolver}, nil
}

type envFirstResolver struct {
	kong.Resolver // Preserve the wrapped resolver's Validate method.
}

func (r envFirstResolver) Resolve(ctx *kong.Context, parent *kong.Path, flag *kong.Flag) (any, error) {
	for _, name := range flag.Tag.Envs {
		if _, present := os.LookupEnv(name); present {
			// Kong has already decoded this environment value. Do not replace it.
			return nil, nil
		}
	}
	return r.Resolver.Resolve(ctx, parent, flag)
}
