# Integration status

The ESG PDF assessment endpoint and React upload panel are integrated into this
project. The endpoint is `POST /api/v1/esg/document-assessment`; the browser
uses the authenticated session and CSRF token rather than a frontend API-key
setting.

For environment setup, Docker Compose deployment, and validation, see
[README.md](./README.md). Do not use prior manual-copy instructions or place
API keys in frontend configuration.
