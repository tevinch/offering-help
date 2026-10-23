package main

import (
	"bytes"
	"strings"
	"testing"
)

const normalized = `normalized[0] 192.0.2.3-192.0.2.8 label="segment-0"
normalized[1] 192.0.2.11-192.0.2.17 label="segment-1"
normalized[2] 192.0.2.30-192.0.2.32 label="segment-2"
normalized[3] 2001:db8::3-2001:db8::8 label="segment-3"
normalized[4] 2001:db8::b-2001:db8::11 label="segment-4"
`

func TestRunCompleteDiagnostics(t *testing.T) {
	var stdout, stderr bytes.Buffer
	status := run(nil, &stdout, &stderr)
	want := normalized + `192.0.2.3 -> index=0 range=192.0.2.3-192.0.2.8 label="segment-0"
192.0.2.9 -> no match
192.0.2.11 -> index=1 range=192.0.2.11-192.0.2.17 label="segment-1"
192.0.2.31 -> index=2 range=192.0.2.30-192.0.2.32 label="segment-2"
2001:db8::3 -> index=3 range=2001:db8::3-2001:db8::8 label="segment-3"
2001:db8::9 -> no match
2001:db8::b -> index=4 range=2001:db8::b-2001:db8::11 label="segment-4"
::ffff:192.0.2.3 -> no match
`
	if status != 0 || stderr.Len() != 0 || stdout.String() != want {
		t.Fatalf("status=%d stderr=%q\noutput:\n%s\nwant:\n%s", status, stderr.String(), stdout.String(), want)
	}
}

func TestRunMalformedAddressContinuesOtherQueries(t *testing.T) {
	var stdout, stderr bytes.Buffer
	status := run([]string{"not-an-address", "192.0.2.11"}, &stdout, &stderr)
	if status != 2 || stderr.String() != "\"not-an-address\": invalid address\n" {
		t.Fatalf("status=%d stderr=%q", status, stderr.String())
	}
	if !strings.HasSuffix(stdout.String(), "192.0.2.11 -> index=1 range=192.0.2.11-192.0.2.17 label=\"segment-1\"\n") {
		t.Fatalf("valid query was not completed: %s", stdout.String())
	}
}
