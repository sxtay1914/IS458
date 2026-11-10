# Browsing stress demo: Mac watcher + CloudShell load

Prepared 10 November 2026. Commands are prepared only; this profile has not been run against the rebuilt stack.

Current website: **https://d1oj35ccg258u3.cloudfront.net**. Cluster: `fashionstore-demo-eks`, region `ap-southeast-1`.

Use the Mac for the watcher because its operator credentials and network access are already configured. Ordinary CloudShell can run the public browsing load without EKS access. Do not copy the Mac's operator credentials into CloudShell.

## 1. Prepare CloudShell before the presentation

Open AWS CloudShell in Singapore. Install k6 if it is missing; these are Grafana's RPM installation commands with automatic confirmation. [Official installation guide](https://grafana.com/docs/k6/latest/set-up/install-k6/)

```bash
if ! command -v k6 >/dev/null 2>&1; then
  sudo dnf install -y https://dl.k6.io/rpm/repo.rpm
  sudo dnf install -y k6
fi

cd "$HOME"
if [ -d IS458/.git ]; then
  git -C IS458 pull --ff-only
else
  git clone https://github.com/sxtay1914/IS458.git IS458
fi
cd IS458/fashionstore
```

The committed [stress profile](../tests/load/profiles/stress.json) ramps from 0 to 150 virtual users in one minute, then to 300 over two minutes, then to 0 over one minute. It reaches 300 near minute three; it does not hold 300 users for the full four minutes. Active iterations may take a little longer to finish. This is the proposed profile from the demo notes, not a verified reconstruction of the November 8 run.

## 2. Start the watcher in Mac Terminal

This uses the current local demo kubeconfig. The first command checks connectivity with a timeout; the watcher starts only if it succeeds.

```bash
export KUBECONFIG=/tmp/fashionstore-demo-session/kubeconfig
kubectl --request-timeout=10s -n fashionstore get hpa store-api-v1 &&
kubectl -n fashionstore get hpa store-api-v1 --watch
```

Show the audience the CPU target/current percentage and `REPLICAS` columns. If the preflight times out after changing Wi-Fi, the new Mac public IP needs to be allowed in EKS first. Do not start the crowd until the watcher works. `Unauthorized` or `Forbidden` means the operator credentials/access need attention instead.

## 3. Start the crowd in CloudShell

From `IS458/fashionstore`, run this about two minutes before showing the scaling slide:

```bash
k6 run \
  -e BASE_URL=https://d1oj35ccg258u3.cloudfront.net \
  -e PROFILE=stress \
  tests/load/browse.js
```

This reuses the existing GET-only browsing script. It does not empty carts, submit checkouts, reset stock or require shopper tokens. Use `stress` with `browse.js` only; the profile has no checkout or flash-sale settings. A purchase made manually during the demo will create an order and reduce stock.

Press **Ctrl+C in CloudShell** to stop the crowd early. Press **Ctrl+C on the Mac** separately to stop watching. After the crowd finishes, leave the watcher open to observe any scale-in.

## 4. Explain the observed result

- "CloudShell is generating browsing traffic while this window shows Kubernetes responding to CPU demand."
- The [current HPA](../platform/kubernetes/base/hpa-v1.yaml) targets **70% CPU utilisation**, with **2–5 v1 replicas**. CPU utilisation is relative to the pods' CPU requests, not the whole EC2 server. [Kubernetes HPA documentation](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- v2 has one separate replica. v1 changing **2 → 3** means total API pods change **3 → 4**. Scaling may go above three v1 pods, or may not occur at all during this run.
- The scale-down stabilisation window is **120 seconds**; this does not guarantee scale-in exactly two minutes after traffic stops.
- Show the actual HPA/k6 output. Use a dated historical screenshot if scaling is too slow, and label it as historical evidence.

Stopping k6 does not stop the AWS stack. Arrange teardown after the presentation; no fixed cost or successful scaling result is claimed for this unrun profile.
