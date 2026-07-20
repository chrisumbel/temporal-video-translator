# Build/push the worker image and deploy the chart (incl. Temporal) to AKS.
#
#   make build    build the docker image
#   make push     push it to the tvttranslator ACR
#   make deploy   helm upgrade --install into the AKS cluster
#   make creds    fetch AKS kubectl credentials
#   make login    switch kubectl's current context to the AKS cluster
#   make test     run the unit tests

VERSION   := $(shell cat VERSION)
ACR       := tvttranslator
IMAGE     := $(ACR).azurecr.io/temporal-video-translator
SS_IMAGE  := $(ACR).azurecr.io/temporal-video-translator-screenshot
CHART     := helm/temporal-video-translator
RELEASE   := temporal-video-translator
NAMESPACE := temporal-video-translator
RG        := temporal-video-translator
CLUSTER   := tvt-aks

.PHONY: build push deploy creds login test

test:
	pytest tests -q

build:
	docker build --target main -t $(IMAGE):$(VERSION) -t $(IMAGE):latest .
	docker build --target screenshot -t $(SS_IMAGE):$(VERSION) -t $(SS_IMAGE):latest .

push: build
	az acr login --name $(ACR)
	docker push $(IMAGE):$(VERSION)
	docker push $(IMAGE):latest
	docker push $(SS_IMAGE):$(VERSION)
	docker push $(SS_IMAGE):latest

deploy:
	helm upgrade --install $(RELEASE) $(CHART) \
		--namespace $(NAMESPACE) --create-namespace \
		-f $(CHART)/secrets.yaml \
		--set image.tag=$(VERSION)

creds:
	az aks get-credentials --resource-group $(RG) --name $(CLUSTER)

login:
	kubectl config use-context $(CLUSTER)
