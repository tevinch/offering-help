package main

import (
	"fmt"
	"io"
	"net/netip"
	"os"

	lookup "github.com/tevinch/offering-help/examples/containing-range"
	"go4.org/netipx"
)

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(queries []string, stdout, stderr io.Writer) int {
	// These arbitrary bounds overlap and touch; removal splits each family.
	inputs := []string{
		"192.0.2.3-192.0.2.8", "192.0.2.7-192.0.2.12", "192.0.2.13-192.0.2.17",
		"192.0.2.30-192.0.2.32", "2001:db8::3-2001:db8::8",
		"2001:db8::7-2001:db8::c", "2001:db8::d-2001:db8::11",
	}
	var builder netipx.IPSetBuilder
	for _, bounds := range inputs {
		builder.AddRange(netipx.MustParseIPRange(bounds))
	}
	builder.RemoveRange(netipx.MustParseIPRange("192.0.2.9-192.0.2.10"))
	builder.RemoveRange(netipx.MustParseIPRange("2001:db8::9-2001:db8::a"))
	set, err := builder.IPSet()
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	index := lookup.New(set)
	ranges := index.Ranges()
	// Values are assigned after normalization and belong to this snapshot.
	labels := make([]string, len(ranges))
	for i, r := range ranges {
		labels[i] = fmt.Sprintf("segment-%d", i)
		fmt.Fprintf(stdout, "normalized[%d] %v label=%q\n", i, r, labels[i])
	}
	if len(queries) == 0 {
		queries = []string{
			"192.0.2.3", "192.0.2.9", "192.0.2.11", "192.0.2.31",
			"2001:db8::3", "2001:db8::9", "2001:db8::b", "::ffff:192.0.2.3",
		}
	}
	status := 0
	for _, text := range queries {
		addr, err := netip.ParseAddr(text)
		if err != nil {
			fmt.Fprintf(stderr, "%q: invalid address\n", text)
			status = 2
			continue
		}
		r, i, found := index.Find(addr)
		if !found {
			fmt.Fprintf(stdout, "%s -> no match\n", text)
			continue
		}
		fmt.Fprintf(stdout, "%s -> index=%d range=%v label=%q\n", text, i, r, labels[i])
	}
	return status
}
