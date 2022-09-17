help:         ## Show this help.
	@sed -ne '/@sed/!s/## //p' $(MAKEFILE_LIST)

build:        ## Build the python module.
	chmod +x scripts/build.sh
	scripts/build.sh

deploy:       ## Applies `build` and uploads the latest version to the Pypi repository.
	chmod +x scripts/deploy.sh
	scripts/deploy.sh

deploy-test:  ## Same as `deploy` but deploys to the Test-Pypi repository.
	chmod +x scripts/deploy-test.sh
	scripts/deploy-test.sh

html:         ## Generate documentation HTML files.
	chmod +x scripts/html.sh
	scripts/html.sh

test:         ## Run all test cases.
	chmod +x scripts/test.sh
	scripts/test.sh


