VERSION := $(shell cat version.txt)
APP_IMAGE_NAME := pr-pilot-app
WORKER_IMAGE_NAME := pr-pilot-worker
REGISTRY_URL := us-west2-docker.pkg.dev/darwin-407004/pr-pilot

build-docker:
	docker build -t $(APP_IMAGE_NAME):$(VERSION) .
	docker build -t $(WORKER_IMAGE_NAME):$(VERSION) -f Dockerfile.worker .
docker-push: build-docker
	docker tag $(APP_IMAGE_NAME):$(VERSION) $(REGISTRY_URL)/$(APP_IMAGE_NAME):$(VERSION)
	docker tag $(APP_IMAGE_NAME):$(VERSION) $(REGISTRY_URL)/$(APP_IMAGE_NAME):latest
	docker push $(REGISTRY_URL)/$(APP_IMAGE_NAME):$(VERSION)
	docker push $(REGISTRY_URL)/$(APP_IMAGE_NAME):latest
	docker tag $(WORKER_IMAGE_NAME):$(VERSION) $(REGISTRY_URL)/$(WORKER_IMAGE_NAME):$(VERSION)
	docker tag $(WORKER_IMAGE_NAME):$(VERSION) $(REGISTRY_URL)/$(WORKER_IMAGE_NAME):latest
	docker push $(REGISTRY_URL)/$(WORKER_IMAGE_NAME):$(VERSION)
	docker push $(REGISTRY_URL)/$(WORKER_IMAGE_NAME):latest
deploy:
	helm package pr-pilot --version $(VERSION) --app-version $(VERSION)
	helm upgrade pr-pilot ./pr-pilot-$(VERSION).tgz --set image.tag=$(VERSION)
create-k8s-secrets:
	kubectl create secret generic pr-pilot-private-key --from-file=github_app_private_key.pem
	kubectl create secret generic pr-pilot-secret --from-env-file=local.env

