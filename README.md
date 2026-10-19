# Offering Help

Small, runnable examples for practical development problems.

- [Export a saved Quill chapter to Markdown with Python](examples/quill-markdown/): preserve text runs, headings and lists without pairing adjacent Delta operations.
- [Synchronous binary stdio with Boa](examples/boa-stdio/): distinguish EOF from errors and read/write Uint8Array views with a complete framed example.
- [Inspect imported ID3 comments before conversion](examples/id3-comment-copy/): omit one selected fallback comment in a new copy while retaining other metadata.
- [Keep Bootstrap form styles with Choices](examples/choices-bootstrap/): enhance searchable selects while retaining ordinary Bootstrap controls and native form values.
- [Read sqlc batch results and Close behavior](examples/sqlc-batch/): map callback indexes to inputs and check actual PostgreSQL rows, rollback and connection reuse.
- [Configure Gateway connection and response timeouts](examples/gateway-timeouts/): distinguish slow response headers from complete large-body transfers with route overrides.

- [Keep Prettier and ESLint class wrapping in Angular](examples/angular-class-format/): preserve ESLint’s static-class layout while formatting the surrounding Angular template.

- [Pass one Helm values file as both YAML and text](examples/helm-values-file/): retain parsed chart settings and a raw-text value with a local rendering check.

- [Check bump.yml version targets before a release](examples/bump-config-check/): validate every configured file, line and version without changing files or running a release.

- [Run PyArrow in a clean Python environment](examples/python-isolation/): keep shared packages out of tests without changing the shared installation.

Each example includes source and instructions to run it. Its guide describes the checked scope. Code is available under the [MIT license](LICENSE).
