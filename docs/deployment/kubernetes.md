# Kubernetes Deployment

This guide covers deploying API Extractor on Kubernetes for production workloads. API Extractor can be deployed as a standalone service or as a sidecar container alongside your application.

## Deployment Patterns

### 1. Standalone Deployment

Deploy API Extractor as a standalone service accessible by all applications in the cluster.

### 2. Sidecar Pattern (Recommended)

Deploy API Extractor as a sidecar container in the same pod as your application for isolated, application-specific API analysis.

## Basic Deployment

### Standalone Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-extractor
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api-extractor
  template:
    metadata:
      labels:
        app: api-extractor
    spec:
      containers:
      - name: api-extractor
        image: api-extractor:latest
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: API_EXTRACTOR_ALLOWED_PATH_PREFIXES
          value: "/app/code"
        - name: API_EXTRACTOR_LOG_LEVEL
          value: "info"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 30
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        volumeMounts:
        - name: code-volume
          mountPath: /app/code
          readOnly: true
      volumes:
      - name: code-volume
        persistentVolumeClaim:
          claimName: code-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: api-extractor
  namespace: default
spec:
  selector:
    app: api-extractor
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
    name: http
  type: ClusterIP
```

### Service Manifest

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api-extractor
  namespace: default
spec:
  selector:
    app: api-extractor
  ports:
  - port: 80
    targetPort: 8000
    name: http
  type: ClusterIP
```

## Sidecar Pattern

Deploy API Extractor alongside your application in the same pod:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      # Main application container
      - name: app
        image: my-app:latest
        ports:
        - containerPort: 8080
          name: http
        volumeMounts:
        - name: app-code
          mountPath: /app/code
          readOnly: true

      # API Extractor sidecar
      - name: api-extractor
        image: api-extractor:latest
        ports:
        - containerPort: 8000
          name: extractor
        env:
        - name: API_EXTRACTOR_ALLOWED_PATH_PREFIXES
          value: "/app/code"
        - name: API_EXTRACTOR_LOG_LEVEL
          value: "info"
        resources:
          requests:
            cpu: 100m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: app-code
          mountPath: /app/code
          readOnly: true

      volumes:
      - name: app-code
        emptyDir: {}
```

## Init Container Pattern

Extract OpenAPI spec before the main application starts:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
spec:
  template:
    spec:
      initContainers:
      - name: extract-api-spec
        image: api-extractor:latest
        command:
        - sh
        - -c
        - |
          echo "Extracting API specification..."
          api-extractor extract /app/code \
            --output /specs/openapi.json \
            --title "User Service API" \
            --version "$APP_VERSION" \
            --verbose

          if [ ! -f /specs/openapi.json ]; then
            echo "ERROR: Failed to extract OpenAPI spec"
            exit 1
          fi

          echo "✓ OpenAPI spec extracted successfully"
          ls -lh /specs/openapi.json
        env:
        - name: APP_VERSION
          valueFrom:
            fieldRef:
              fieldPath: metadata.labels['version']
        volumeMounts:
        - name: app-code
          mountPath: /app/code
          readOnly: true
        - name: api-specs
          mountPath: /specs

      containers:
      - name: app
        image: user-service:latest
        env:
        - name: OPENAPI_SPEC_PATH
          value: /specs/openapi.json
        volumeMounts:
        - name: api-specs
          mountPath: /specs
          readOnly: true

      volumes:
      - name: app-code
        emptyDir: {}
      - name: api-specs
        emptyDir: {}
```

## Storage Options

### EmptyDir Volume (Ephemeral)

Best for sidecar pattern where code is copied at startup:

```yaml
volumes:
- name: app-code
  emptyDir: {}
```

### PersistentVolumeClaim

Best for standalone deployment with shared code:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: code-pvc
spec:
  accessModes:
    - ReadOnlyMany
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard
---
volumes:
- name: code-volume
  persistentVolumeClaim:
    claimName: code-pvc
```

### ConfigMap for Small Projects

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-source
data:
  main.py: |
    from fastapi import FastAPI
    app = FastAPI()

    @app.get("/users")
    def get_users():
        return {"users": []}
---
volumes:
- name: app-code
  configMap:
    name: app-source
```

### HostPath (Development Only)

**Warning**: Not recommended for production.

```yaml
volumes:
- name: app-code
  hostPath:
    path: /path/to/code
    type: Directory
```

## Configuration

### Using ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-extractor-config
data:
  API_EXTRACTOR_LOG_LEVEL: "info"
  API_EXTRACTOR_ALLOWED_PATH_PREFIXES: "/app/code,/app/shared"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-extractor
spec:
  template:
    spec:
      containers:
      - name: api-extractor
        image: api-extractor:latest
        envFrom:
        - configMapRef:
            name: api-extractor-config
```

### Using Secrets

For sensitive configuration (though API Extractor typically doesn't need secrets):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-extractor-secrets
type: Opaque
stringData:
  API_KEY: "your-secret-key"
---
containers:
- name: api-extractor
  envFrom:
  - secretRef:
      name: api-extractor-secrets
```

## Resource Management

### Resource Requests and Limits

```yaml
resources:
  requests:
    cpu: 250m        # Minimum guaranteed CPU
    memory: 512Mi    # Minimum guaranteed memory
  limits:
    cpu: 1000m       # Maximum CPU (1 core)
    memory: 1Gi      # Maximum memory
```

### Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-extractor-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-extractor
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Ingress Configuration

### NGINX Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-extractor
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api-extractor.example.com
    secretName: api-extractor-tls
  rules:
  - host: api-extractor.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-extractor
            port:
              number: 80
```

### Traefik Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-extractor
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
spec:
  rules:
  - host: api-extractor.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-extractor
            port:
              number: 80
```

## Service Mesh Integration

### Istio

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: api-extractor
spec:
  hosts:
  - api-extractor
  http:
  - route:
    - destination:
        host: api-extractor
        port:
          number: 80
    timeout: 60s
    retries:
      attempts: 3
      perTryTimeout: 20s
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: api-extractor
spec:
  host: api-extractor
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
```

## Monitoring

### Prometheus ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: api-extractor
spec:
  selector:
    matchLabels:
      app: api-extractor
  endpoints:
  - port: http
    interval: 30s
    path: /api/v1/health
```

### Pod Disruption Budget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-extractor-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: api-extractor
```

## Security

### NetworkPolicy

Restrict traffic to API Extractor:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-extractor-netpol
spec:
  podSelector:
    matchLabels:
      app: api-extractor
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: default
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 53  # DNS
```

### Security Context

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
  containers:
  - name: api-extractor
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -l app=api-extractor
kubectl describe pod <pod-name>
```

### View Logs

```bash
# All pods
kubectl logs -l app=api-extractor --tail=100 -f

# Specific pod
kubectl logs <pod-name> --tail=100 -f

# Specific container in sidecar pattern
kubectl logs <pod-name> -c api-extractor
```

### Test Service

```bash
# Port forward to local machine
kubectl port-forward svc/api-extractor 8000:80

# Test health endpoint
curl http://localhost:8000/api/v1/health

# Test extraction
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"path": "/app/code"}'
```

### Debug Container

```bash
# Execute shell in pod
kubectl exec -it <pod-name> -- /bin/sh

# In sidecar pattern
kubectl exec -it <pod-name> -c api-extractor -- /bin/sh

# Check filesystem
kubectl exec <pod-name> -c api-extractor -- ls -la /app/code
```

### Common Issues

**Pods not starting:**
- Check image pull secrets: `kubectl describe pod <pod-name>`
- Verify resource requests fit node capacity
- Check volume mounts are correct

**Health checks failing:**
- Increase `initialDelaySeconds` if container needs more startup time
- Check if application is listening on correct port
- Verify network policies aren't blocking traffic

**403 Forbidden errors:**
- Check `API_EXTRACTOR_ALLOWED_PATH_PREFIXES` includes requested paths
- Verify volume is mounted at correct path
- Ensure path doesn't contain `..` or target system directories

## Complete Example

Here's a complete production-ready deployment:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: api-tools
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-extractor-config
  namespace: api-tools
data:
  API_EXTRACTOR_LOG_LEVEL: "info"
  API_EXTRACTOR_ALLOWED_PATH_PREFIXES: "/app/code"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-extractor
  namespace: api-tools
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  selector:
    matchLabels:
      app: api-extractor
  template:
    metadata:
      labels:
        app: api-extractor
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: api-extractor
        image: api-extractor:v1.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: api-extractor-config
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        volumeMounts:
        - name: code-volume
          mountPath: /app/code
          readOnly: true
      volumes:
      - name: code-volume
        persistentVolumeClaim:
          claimName: code-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: api-extractor
  namespace: api-tools
spec:
  selector:
    app: api-extractor
  ports:
  - port: 80
    targetPort: 8000
    name: http
  type: ClusterIP
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-extractor-pdb
  namespace: api-tools
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: api-extractor
```

## See Also

- [HTTP Server Guide](http-server.md) - HTTP API documentation
- [Docker Deployment](docker.md) - Docker setup and configuration
- [AWS Lambda Deployment](lambda.md) - Serverless deployment
