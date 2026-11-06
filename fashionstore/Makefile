TF        ?= terraform
TF_DIR    := infra/terraform
DEMO_DIR  := $(TF_DIR)/environments/demo
BOOT_DIR  := $(TF_DIR)/bootstrap

.PHONY: fmt validate bootstrap init-demo plan-demo deploy-demo destroy-demo

fmt:
	$(TF) fmt -recursive $(TF_DIR)

validate:
	$(TF) fmt -check -recursive $(TF_DIR)
	$(TF) -chdir=$(BOOT_DIR) init -backend=false -input=false >/dev/null
	$(TF) -chdir=$(BOOT_DIR) validate
	$(TF) -chdir=$(DEMO_DIR) init -backend=false -input=false >/dev/null
	$(TF) -chdir=$(DEMO_DIR) validate

bootstrap:
	$(TF) -chdir=$(BOOT_DIR) init
	$(TF) -chdir=$(BOOT_DIR) apply

init-demo:
	$(TF) -chdir=$(DEMO_DIR) init -backend-config=backend.hcl

plan-demo:
	$(TF) -chdir=$(DEMO_DIR) plan -out=demo.tfplan

deploy-demo: plan-demo
	$(TF) -chdir=$(DEMO_DIR) apply demo.tfplan

# Delete Kubernetes-owned AWS resources first (TargetGroupBinding etc.)
# once workloads exist, or the destroy stalls on ENIs / security groups.
destroy-demo:
	-kubectl delete -k platform/kubernetes/overlays/demo --ignore-not-found
	$(TF) -chdir=$(DEMO_DIR) destroy
