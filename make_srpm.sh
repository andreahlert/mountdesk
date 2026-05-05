#!/bin/bash
set -e

VERSION=$(grep '^Version:' rpm/mountdesk.spec | awk '{print $2}')
NAME=mountdesk
OUTDIR=${1:-.}

# Create source tarball
TMPDIR=$(mktemp -d)
mkdir -p "$TMPDIR/$NAME-$VERSION"
cp -r src rpm LICENSE README.md assets "$TMPDIR/$NAME-$VERSION/"
cd "$TMPDIR"
tar czf "$OUTDIR/$NAME-$VERSION.tar.gz" "$NAME-$VERSION"
cd -
rm -rf "$TMPDIR"

# Build SRPM
mkdir -p ~/rpmbuild/SPECS ~/rpmbuild/SOURCES
cp rpm/mountdesk.spec ~/rpmbuild/SPECS/
cp "$OUTDIR/$NAME-$VERSION.tar.gz" ~/rpmbuild/SOURCES/
cd ~/rpmbuild/SPECS
rpmbuild -bs mountdesk.spec --define "_srcrpmdir $OUTDIR"
