# Environment
- One Kubernetes cluster
- API Gateway deployed in *gateway-namespace*
- APIs deployed in various namespaces
- Logging framework using a Splunk instace for visualization and FluentBit as a logs exporter from API Gateway / APIs to Splunk

# Security
- Kubernetes NetworkPolicy in place that restricts traffic to the APIs (only allowing traffic from API Gateway)
- Splunk traffic to HEC is restricted to only FluentBit exporter
- Traffic to FluentBit exporter is restricted to API Gateway and APIs

# Authentication and Authorization
- Using JWT tokens (with lifespan) 
- Using Roles for endpoint rules

# Tracing
- API Gateway supports tracing by creating / maintaining a X-Request-ID

# Rate Limiting
- Rate limit per User (not token, but user, because more tokens can be created) (Prevents abuse from individual users)
- Rate limit per API (Protect APIs from overload)

# Centralized Automatic Documentation
- Using the auto generated OpenAPI specification by FastAPI the API Gateway aggregates all APIs documentation
- Only onboarded endpoints will appear in the aggregated documentation
- The documentation of the APIs can be grouped by a common tag specified in onboarding
- Same API can be differentiated by version

# Versioning
- The API Gateway can version APIs by specifying it in the onboarding information 

# Improvements
- Use OAuth or something else for Auth/Authz
- Add retries to FluentBit exporter?
- Dashboard for FluentBit metrics ?
- Do something with FluentBit metrics / health?
- Create dashboard in Splunk
- Set alarms in Splunk for abusing API Gateway (rate limiting)
- Prometheus + Grafana for visualization for API Gateway metrics?