NAME = mountdesk
VERSION = 1.0.1
SPEC = rpm/$(NAME).spec

.PHONY: all rpm clean install

all: rpm

rpm:
	mkdir -p ~/rpmbuild/{SPECS,SOURCES,BUILD,RPMS,SRPMS}
	cp $(SPEC) ~/rpmbuild/SPECS/
	tar czf ~/rpmbuild/SOURCES/$(NAME)-$(VERSION).tar.gz \
		--transform 's,^,$(NAME)-$(VERSION)/,' \
		src rpm LICENSE README.md
	cd ~/rpmbuild/SPECS && rpmbuild -ba $(NAME).spec
	@echo "RPM built:"
	@ls -lh ~/rpmbuild/RPMS/noarch/$(NAME)-$(VERSION)*.rpm

install:
	sudo dnf install ~/rpmbuild/RPMS/noarch/$(NAME)-$(VERSION)*.rpm

clean:
	rm -rf ~/rpmbuild/BUILD/$(NAME)-* \
		~/rpmbuild/BUILDROOT/$(NAME)-* \
		~/rpmbuild/RPMS/noarch/$(NAME)-* \
		~/rpmbuild/SRPMS/$(NAME)-* \
		~/rpmbuild/SOURCES/$(NAME)-*.tar.gz
