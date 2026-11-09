SHELL     := /bin/bash
TF        ?= terraform
TF_DIR    := infra/terraform
DEMO_DIR  := $(TF_DIR)/environments/demo
BOOT_DIR  := $(TF_DIR)/bootstrap
MODULE_DIRS := $(patsubst %/tests/,%,$(sort $(dir $(wildcard $(TF_DIR)/modules/*/tests/*.tftest.hcl))))
FUNCTIONS := process-checkout payment-api notifier report
K8S_NS    := fashionstore
DB_URL    ?= jdbc:mysql://127.0.0.1:3306/fashionstore?allowPublicKeyRetrieval=true&useSSL=false
OUT       = $(TF) -chdir=$(DEMO_DIR) output

.PHONY: help fmt validate test tf-test py-test api-test web-test e2e db-local-up db-migrate db-seed \
        package api-run bootstrap init-demo plan-demo deploy-demo k8s-config addons k8s-apply \
        db-migrate-remote db-seed-remote push-api deploy-storefront test-users smoke verify-private \
        live-test e2e-live load-browse load-checkout load-flash dashboard destroy-demo

help:
	@grep -E '^[a-z0-9-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-20s %s\n", $$1, $$2}'

# ---------------------------------------------------------------- checks (no AWS needed)
fmt: ## terraform fmt everything
	$(TF) fmt -recursive $(TF_DIR)

validate: ## fmt check + validate bootstrap and demo
	$(TF) fmt -check -recursive $(TF_DIR)
	$(TF) -chdir=$(BOOT_DIR) init -backend=false -input=false >/dev/null && $(TF) -chdir=$(BOOT_DIR) validate
	$(TF) -chdir=$(DEMO_DIR) init -backend=false -input=false >/dev/null && $(TF) -chdir=$(DEMO_DIR) validate

tf-test: ## terraform test (mocked AWS) for every module, bootstrap and demo
	@set -e; for d in $(MODULE_DIRS) $(BOOT_DIR) $(DEMO_DIR); do \
	  echo "== $$d"; $(TF) -chdir=$$d init -backend=false -input=false >/dev/null; $(TF) -chdir=$$d test; done

py-test: ## pytest every Lambda against MySQL 8 (make db-local-up first)
	@set -e; for f in $(FUNCTIONS); do echo "== $$f"; python3 -m pytest -q -p no:cacheprovider functions/$$f/tests; done

api-test: ## store-api: JUnit + Testcontainers MySQL (needs Docker)
	cd apps/store-api && ./mvnw -B -q test

web-test: ## storefront: typecheck, vitest, production build
	cd apps/storefront && npm ci --no-audit --no-fund && npm run typecheck && npm test && npm run build

e2e: ## Playwright against the built storefront with a mocked backend
	cd tests/e2e && npm ci --no-audit --no-fund && npx playwright test

test: validate tf-test py-test api-test web-test e2e ## everything above

api-run: ## run store-api locally on :8080 (local MySQL, in-memory messaging)
	cd apps/store-api && SPRING_PROFILES_ACTIVE=local ./mvnw -B spring-boot:run

db-local-up: ## start local MySQL 8 in Docker
	docker run -d --name fsdb -e MYSQL_ROOT_PASSWORD=root -e MYSQL_DATABASE=fashionstore -p 3306:3306 mysql:8.4
	@until docker exec fsdb mysqladmin -proot ping >/dev/null 2>&1; do sleep 2; done; echo "MySQL ready"

db-migrate: ## Flyway migrate the local database
	docker run --rm --network host -v $(CURDIR)/database/migrations:/flyway/sql flyway/flyway:10 \
	  -url='$(DB_URL)' -user=root -password=root migrate info

db-seed: ## load seeds into the local database
	for f in products inventory; do docker exec -i fsdb mysql -uroot -proot fashionstore < database/seeds/$$f.sql; done

package: ## build build/functions/*.zip
	./scripts/package-functions.sh

# ---------------------------------------------------------------- AWS
bootstrap: ## once per account: state bucket, CI roles, budget
	$(TF) -chdir=$(BOOT_DIR) init && $(TF) -chdir=$(BOOT_DIR) apply

init-demo: ## terraform init with backend.hcl
	$(TF) -chdir=$(DEMO_DIR) init -backend-config=backend.hcl

plan-demo: package ## package Lambdas, then plan
	$(TF) -chdir=$(DEMO_DIR) plan -out=demo.tfplan

deploy-demo: plan-demo ## package, plan, apply
	$(TF) -chdir=$(DEMO_DIR) apply demo.tfplan

k8s-config: ## kubeconfig + overlay env files from terraform outputs (V1_TAG=.. V2_TAG=..)
	./scripts/render-k8s-config.sh $(or $(V1_TAG),v1) $(or $(V2_TAG),v2)
	aws eks update-kubeconfig --region ap-southeast-1 --name $$($(OUT) -raw eks_cluster_name)

addons: ## helm: metrics-server, cluster-autoscaler, aws-load-balancer-controller
	helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/ >/dev/null
	helm repo add autoscaler https://kubernetes.github.io/autoscaler >/dev/null
	helm repo add eks https://aws.github.io/eks-charts >/dev/null
	helm repo update >/dev/null
	helm upgrade --install metrics-server metrics-server/metrics-server -n kube-system \
	  -f platform/addons/metrics-server/values.yaml
	helm upgrade --install cluster-autoscaler autoscaler/cluster-autoscaler -n kube-system \
	  -f platform/addons/cluster-autoscaler/values.yaml \
	  --set "rbac.serviceAccount.annotations.eks\.amazonaws\.com/role-arn=$$($(OUT) -json irsa_role_arns | python3 -c 'import json,sys;print(json.load(sys.stdin)["cluster-autoscaler"])')"
	helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller -n kube-system \
	  -f platform/addons/aws-load-balancer-controller/values.yaml \
	  --set vpcId=$$($(OUT) -raw vpc_id) \
	  --set "serviceAccount.annotations.eks\.amazonaws\.com/role-arn=$$($(OUT) -json irsa_role_arns | python3 -c 'import json,sys;print(json.load(sys.stdin)["aws-load-balancer-controller"])')"

k8s-apply: ## apply the demo overlay (store-api v1 + v2, TargetGroupBindings, HPA)
	kubectl apply -k platform/kubernetes/overlays/demo

db-migrate-remote: ## Flyway Job against RDS from inside the cluster
	kubectl kustomize platform/kubernetes/overlays/demo \
	  | python3 scripts/select-kinds.py Namespace ServiceAccount ConfigMap | kubectl apply -f -
	kubectl -n $(K8S_NS) create configmap flyway-migrations --from-file=database/migrations \
	  --from-file=rds-ca.pem=functions/common/fashionstore_common/rds-ca.pem \
	  --dry-run=client -o yaml | kubectl apply -f -
	kubectl -n $(K8S_NS) delete job database-migration --ignore-not-found
	kubectl apply -f platform/kubernetes/jobs/database-migration.yaml
	kubectl -n $(K8S_NS) wait --for=condition=complete job/database-migration --timeout=300s
	kubectl -n $(K8S_NS) logs job/database-migration -c flyway

db-seed-remote: ## seed products + inventory on RDS
	kubectl -n $(K8S_NS) create configmap db-seeds --from-file=database/seeds \
	  --dry-run=client -o yaml | kubectl apply -f -
	kubectl -n $(K8S_NS) delete job seed-demo --ignore-not-found
	kubectl apply -f platform/kubernetes/jobs/seed-demo.yaml
	kubectl -n $(K8S_NS) wait --for=condition=complete job/seed-demo --timeout=300s
	kubectl -n $(K8S_NS) logs job/seed-demo -c seed

push-api: ## build + push the store-api image to ECR (TAG=... default git sha)
	./scripts/build-push-api.sh $(TAG)

deploy-storefront: ## build the SPA, write config.json, sync to S3, invalidate CloudFront
	./scripts/deploy-storefront.sh

test-users: ## create Cognito test shoppers (EMAILS="a@x b@x", TEST_USER_PASSWORD=...)
	./scripts/create-test-users.sh $(EMAILS)

smoke: ## live: one checkout SQS -> Lambda -> RDS -> SNS -> email (SMOKE_EMAIL=...)
	./tests/infrastructure/smoke-test.sh

verify-private: ## live: ALB internal, RDS private, S3 403, CloudFront OK
	./tests/infrastructure/verify-private-resources.sh

SITE = $$($(OUT) -raw storefront_url)

live-test: ## live pytest: security, correctness, failure (FS_* env vars, see tests/conftest.py)
	URL=$${FS_BASE_URL:-$(SITE)}; cd tests && FS_BASE_URL=$$URL python3 -m pytest -v

e2e-live: ## Playwright against CloudFront + real Cognito (E2E_* env vars)
	URL=$${E2E_BASE_URL:-$(SITE)}; cd tests/e2e && E2E_BASE_URL=$$URL npx playwright test

load-browse: ## k6 browse (PROFILE=smoke|demo)
	k6 run -e BASE_URL=$(SITE) -e PROFILE=$(or $(PROFILE),smoke) tests/load/browse.js

load-checkout: ## k6 checkout (needs tests/load/tokens.json)
	k6 run -e BASE_URL=$(SITE) -e PROFILE=$(or $(PROFILE),smoke) tests/load/checkout.js

load-flash: ## k6 flash sale on FLASH-001 (reseed first: make db-seed-remote)
	k6 run -e BASE_URL=$(SITE) -e PROFILE=$(or $(PROFILE),smoke) tests/load/flash-sale.js

dashboard: ## launch the interactive Streamlit test controller
	@which uv >/dev/null 2>&1 && uv run --with streamlit --with boto3 --with requests --with pytest --with pandas streamlit run dashboard/app.py || streamlit run dashboard/app.py

# ---------------------------------------------------------------- teardown (manual)
destroy-demo: ## steps 2-4 of the teardown checklist in docs/implementation-plan.md
	-kubectl delete -k platform/kubernetes/overlays/demo --ignore-not-found
	-helm uninstall aws-load-balancer-controller cluster-autoscaler metrics-server -n kube-system
	$(TF) -chdir=$(DEMO_DIR) destroy
