"""Filter a multi-document Kubernetes YAML stream on stdin down to the given kinds.

Used by `make db-migrate-remote` to apply only the Namespace, ServiceAccount and
ConfigMaps (no Deployments) before store-api exists.
Text-based split so it needs no PyYAML.
"""
import re
import sys

kinds = set(sys.argv[1:])
docs = re.split(r"^---\s*$", sys.stdin.read(), flags=re.MULTILINE)
out = []
for doc in docs:
    m = re.search(r"^kind:\s*(\S+)", doc, flags=re.MULTILINE)
    if m and m.group(1) in kinds:
        out.append(doc.strip("\n"))
sys.stdout.write("\n---\n".join(out) + "\n")
