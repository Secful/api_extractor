# Hackathon Starter - Express.js Repository Analysis

## Repository Information
- **GitHub URL:** https://github.com/sahat/hackathon-starter
- **Stars:** 35,216
- **Last Updated:** 2026-04-27
- **Language:** JavaScript
- **License:** MIT

## Selection Rationale
A comprehensive Express.js boilerplate demonstrating 25+ third-party API integrations, multiple authentication strategies (OAuth, WebAuthn, 2FA), payment processing (Stripe, PayPal), and modern AI/ML features, providing maximum pattern diversity compared to RealWorld's focused blogging platform - ideal for stress-testing extractor capabilities across authentication flows, payment processing, file uploads, rate limiting, and service integrations.

## Scoring

| Criterion | Score | Notes |
|-----------|-------|-------|
| Active Maintenance | 10/10 | Last commit April 27, 2026 (1 day ago), consistent updates |
| Code Quality | 10/10 | 8,488 LOC tests, CI/CD (multi-OS), ESLint, Prettier, c8 coverage, Playwright E2E, husky hooks |
| Endpoint Count | 10/10 | 106 endpoints (beyond ideal range but excellent for stress testing) |
| Framework Usage | 10/10 | Express with extensive middleware ecosystem (Passport, Lusca, rate-limit, session) |
| Pattern Diversity | 10/10 | OAuth (8 providers), WebAuthn, 2FA, payments, file upload, rate limiting, CSRF, AI/ML |
| Production Usage | 5/5 | Live demo at hackathon-starter-1.ydftech.com, production checklist, real user testimonials |
| Documentation | 5/5 | Extensive README, tutorials, cheatsheets, TESTING.md, prod-checklist.md |
| Stars/Popularity | 5/5 | 35,216 stars (one of most popular Node.js boilerplates) |
| **TOTAL** | **60/60** | **PASS (Perfect Score)** |

## Application Overview

- **Domain:** Multi-Service Integration Hub / Boilerplate Application
- **Description:** Production-ready starter kit for rapid prototyping with extensive examples of authentication methods, payment processing, third-party API integrations (25+ services), AI/ML capabilities, and modern web development patterns
- **Key Features:**
  - Multiple authentication strategies (local, OAuth 2.0, OAuth 1.0a, OpenID, WebAuthn, passwordless)
  - Two-factor authentication (email codes, TOTP)
  - Payment processing (Stripe, PayPal)
  - File upload with CSRF protection
  - Tiered rate limiting
  - AI/ML integration (LangChain, Groq, Hugging Face, RAG, vector search)
  - Third-party API examples (GitHub, Google, Twilio, Facebook, etc.)
  - Email services (Nodemailer with multiple transports)
  - Web scraping (Cheerio)
  - Server-side rendering (Pug templates)
  - Session management (MongoDB-backed)
  - Production security (CSRF, XSS protection, rate limiting)

## API Structure

### Expected Endpoint Count
**Estimated:** 106 endpoints

### Key Endpoint Categories

**Authentication & Account Management (38 endpoints):**
- Local authentication (login, signup, logout)
- OAuth 2.0 providers (Google, Facebook, GitHub, LinkedIn, Instagram, Twitch, Pinterest, OpenCollective)
- OAuth 1.0a (Tumblr)
- OpenID (Steam)
- WebAuthn/Passkeys registration and authentication
- Passwordless authentication
- Two-factor authentication (email codes, TOTP setup/verification)
- Email verification
- Password reset flows
- Account deletion
- Token revocation

**API Integration Examples (33 endpoints):**
- Payment: Stripe checkout, PayPal checkout
- Communication: Twilio SMS
- Social: Facebook, Tumblr, Twitch profile data
- Cloud: Google Maps, Google Drive, Google Sheets
- Location: Foursquare, HERE Maps
- Media: Last.fm, Steam, GIPHY
- Data: NYT articles, Wikipedia, PubChem
- Entertainment: Trakt TV
- Mail: Lob letter sending

**AI/ML Features (10 endpoints):**
- OpenAI moderation
- LLM text classifier
- LLM camera vision (image analysis)
- RAG (Retrieval Augmented Generation) with vector search
- AI agent with tool calling and checkpoints
- Semantic caching

**OAuth Callbacks (20 endpoints):**
- Authentication callbacks for all OAuth providers
- Success and failure handlers

**Core Application (5 endpoints):**
- Home page
- Contact form
- Logout
- Auth failure handler
- Upload handler

### Sample Endpoints

| Method | Path | Purpose | Parameters | Notes |
|--------|------|---------|------------|-------|
| GET | / | Home page | - | Public |
| GET | /login | Login page | - | Public |
| POST | /login | Process login | email, password | Local auth |
| GET | /logout | Logout user | - | Requires auth |
| GET | /signup | Signup page | - | Public |
| POST | /signup | Create account | email, password | Registration |
| GET | /account | Account settings | - | Requires auth |
| POST | /account/profile | Update profile | name, email, location | Requires auth |
| POST | /account/password | Change password | password, confirmPassword | Requires auth |
| POST | /account/delete | Delete account | - | Requires auth |
| GET | /account/unlink/:provider | Unlink OAuth | provider (path) | OAuth management |
| GET | /reset/:token | Password reset | token (path) | Reset flow |
| POST | /reset/:token | Process reset | password | Reset flow |
| GET | /forgot | Forgot password | - | Public |
| POST | /forgot | Send reset email | email | Email service |
| GET | /auth/google | Google OAuth | - | OAuth initiation |
| GET | /auth/google/callback | OAuth callback | code (query) | OAuth flow |
| GET | /auth/github | GitHub OAuth | - | OAuth initiation |
| GET | /auth/github/callback | OAuth callback | code (query) | OAuth flow |
| GET | /webauthn/register | WebAuthn register | - | Requires auth |
| POST | /webauthn/register | Process WebAuthn | publicKey, ... | Passkey creation |
| GET | /webauthn/login | WebAuthn login | - | Public |
| POST | /webauthn/login | Verify WebAuthn | credential | Passwordless |
| GET | /two-factor/setup | 2FA setup page | - | Requires auth |
| POST | /two-factor/enable | Enable TOTP | token | 2FA activation |
| POST | /two-factor/verify | Verify 2FA code | token | Login flow |
| POST | /two-factor/disable | Disable 2FA | password | 2FA removal |
| GET | /api/stripe | Stripe example | - | Payment demo |
| POST | /api/stripe | Process payment | stripeToken | Stripe integration |
| GET | /api/paypal | PayPal example | - | Payment demo |
| POST | /api/paypal | Process payment | - | PayPal integration |
| GET | /api/paypal/success | Payment success | - | Payment callback |
| GET | /api/paypal/cancel | Payment cancel | - | Payment callback |
| GET | /api/twilio | Twilio example | - | SMS demo |
| POST | /api/twilio | Send SMS | number, message | Twilio integration |
| GET | /api/upload | Upload example | - | File upload demo |
| POST | /api/upload | Process upload | file (multipart) | File upload with CSRF |
| GET | /api/facebook | Facebook graph | - | Social API |
| GET | /api/github | GitHub repos | - | Social API |
| GET | /api/google-maps | Maps API | - | Location API |
| GET | /api/google-sheets | Sheets API | - | Cloud API |
| GET | /ai/moderation | Content moderation | - | OpenAI integration |
| POST | /ai/moderation | Moderate content | text | AI moderation |
| GET | /ai/llm | LLM classifier | - | AI demo |
| POST | /ai/llm | Classify text | text | LLM integration |
| GET | /ai/camera | Vision API | - | AI vision demo |
| POST | /ai/camera | Analyze image | image | Computer vision |
| GET | /ai/rag | RAG example | - | Vector search demo |
| POST | /ai/rag | Query RAG | query | Semantic search |
| GET | /ai/agent | AI agent demo | - | Agent example |
| POST | /ai/agent | Run agent | task | LangGraph agent |
| GET | /contact | Contact page | - | Public |
| POST | /contact | Send contact | name, email, message | Email service |

## Notable Patterns

### 1. Multiple Authentication Strategies
- Local (email/password)
- OAuth 2.0 (8 providers: Google, Facebook, GitHub, LinkedIn, Instagram, Twitch, Pinterest, OpenCollective)
- OAuth 1.0a (Tumblr)
- OpenID (Steam)
- WebAuthn/Passkeys
- Passwordless
- Files: `/config/passport.js`, `/controllers/user.js`

### 2. Two-Factor Authentication (2FA)
- Email-based OTP codes
- Time-based One-Time Passwords (TOTP) with QR codes
- 2FA verification during login
- 2FA management (enable/disable)
- Files: `/controllers/user.js` (2FA methods)

### 3. Payment Processing
- Stripe integration with checkout flows
- PayPal integration with success/cancel callbacks
- Webhook handling for payment events
- Files: `/controllers/api.js` (Stripe, PayPal endpoints)

### 4. OAuth Flow Management
- Authorization initiation endpoints
- Callback handlers for all providers
- Token revocation
- Account linking/unlinking
- Files: `/config/passport.js`, `/controllers/user.js`

### 5. File Upload with Security
- Multer-based multipart file handling
- CSRF protection with Lusca
- File validation
- Files: `/controllers/api.js` (upload endpoint)

### 6. Tiered Rate Limiting
- Global rate limit (100 req/15min)
- Strict rate limit (5 req/15min for sensitive ops)
- Login-specific rate limit (5 attempts/hour)
- 2FA-specific rate limit
- Files: `/app.js` (middleware configuration)

### 7. Session Management
- MongoDB-backed sessions with connect-mongo
- Secure session configuration
- Session persistence across restarts
- Files: `/app.js` (session middleware)

### 8. Email Services
- Nodemailer integration
- Multiple transport options (SMTP, AWS SES, Mailgun)
- Email verification flows
- Password reset emails
- Contact form emails
- Files: `/controllers/user.js`, `/controllers/contact.js`

### 9. AI/ML Integration
- LangChain with Groq and Hugging Face
- MongoDB vector store for RAG
- Semantic caching
- AI agents with checkpoints (LangGraph)
- OpenAI moderation API
- Computer vision with image analysis
- Files: `/controllers/ai.js`

### 10. Security Patterns
- CSRF protection with Lusca
- XSS protection
- Helmet security headers
- Rate limiting on sensitive endpoints
- Input validation with express-validator
- Secure password storage with bcrypt
- Files: `/app.js` (middleware)

### 11. Third-Party API Integration
- Consistent pattern for API examples
- Error handling for API failures
- API key management through environment variables
- Rate limit handling
- Files: `/controllers/api.js`

### 12. Server-Side Rendering
- Pug template engine
- Flash messages
- Form validation errors
- CSRF tokens in forms
- Files: `/views/*.pug`

## Expected Extraction Results

**Success Criteria:**
- `result.success == True`
- `len(result.endpoints) >= 80` (may not capture all dynamically generated OAuth callbacks)
- HTTP methods: GET, POST present (primary methods)
- Path parameters extracted correctly (`:provider`, `:token`)
- Express route patterns detected
- Multiple routers detected (main app routes, API routes)
- Source tracking present

**Known Edge Cases:**
1. OAuth callback routes - may have dynamic provider names
2. Template rendering routes - GET endpoints serving HTML, not REST API
3. Middleware chains - shouldn't extract middleware as endpoints
4. Static file serving - shouldn't extract static routes
5. Error handlers - shouldn't extract 404/500 handlers as endpoints
6. Nested route parameters (`:provider`, `:token`) - should convert to OpenAPI format
7. WebAuthn binary data - complex request/response bodies
8. AI/ML endpoints - may have streaming responses
9. File upload endpoints - multipart/form-data content type
10. Rate-limited endpoints - may have different middleware

## Special Considerations

### Dependencies
- Database: MongoDB (required for sessions, users, AI vector store)
- Runtime: Node.js 18+
- Express 4.19+
- Passport.js (authentication)
- LangChain (AI/ML features)
- Multer (file uploads)
- Nodemailer (email)

### Excluded Files/Directories
- Tests: `test/`, `*.test.js`
- Build: `dist/`, `.cache/`
- Dependencies: `node_modules/`
- Assets: `public/`, `uploads/`
- Views: `views/` (Pug templates, not API code)
- Config: `.env`, `*.config.js`

### Extractor Challenges
1. **Template routes vs API routes** - Many endpoints serve HTML (Pug templates), not REST API responses
2. **OAuth dynamic routes** - Multiple providers with similar patterns (`/auth/:provider`, `/auth/:provider/callback`)
3. **Middleware chains** - Complex middleware stacks (auth, rate-limit, CSRF) shouldn't be extracted as endpoints
4. **Route parameter conversion** - Express `:param` to OpenAPI `{param}` format
5. **Passport.js integration** - OAuth routes created by Passport middleware, may not be explicitly defined
6. **Binary data handling** - WebAuthn and file uploads have complex binary payloads
7. **AI/ML streaming** - Some AI endpoints may use streaming responses
8. **Mixed API + web** - Application has both web pages and API endpoints in same routes
9. **Flash messages** - Session-based flash messages used for web pages
10. **CSRF tokens** - Web forms require CSRF tokens, API endpoints may not

## Integration Test Plan

### Test File
`tests/integration/test_realworld_express_hackathon_starter.py`

### Test Assertions
```python
# Basic extraction
assert result.success
assert len(result.endpoints) >= 80  # May not capture all OAuth dynamic routes

# HTTP methods
methods = {ep.method for ep in result.endpoints}
assert HTTPMethod.GET in methods
assert HTTPMethod.POST in methods

# Authentication endpoints
paths = {ep.path for ep in result.endpoints}
assert "/login" in paths
assert "/signup" in paths
assert "/logout" in paths
assert "/account" in paths

# OAuth patterns (with or without /auth prefix)
oauth_endpoints = [ep for ep in result.endpoints if "google" in ep.path or "github" in ep.path]
assert len(oauth_endpoints) >= 4  # At least 2 providers with callback

# 2FA endpoints
tfa_endpoints = [ep for ep in result.endpoints if "two-factor" in ep.path]
assert len(tfa_endpoints) >= 3  # Setup, enable, verify, disable

# WebAuthn endpoints
webauthn_endpoints = [ep for ep in result.endpoints if "webauthn" in ep.path]
assert len(webauthn_endpoints) >= 2  # Register, login

# Payment endpoints
payment_endpoints = [ep for ep in result.endpoints if "stripe" in ep.path or "paypal" in ep.path]
assert len(payment_endpoints) >= 4  # Stripe, PayPal with callbacks

# API integration endpoints
api_endpoints = [ep for ep in result.endpoints if ep.path.startswith("/api/")]
assert len(api_endpoints) >= 15  # Many third-party API examples

# AI/ML endpoints
ai_endpoints = [ep for ep in result.endpoints if "/ai/" in ep.path]
assert len(ai_endpoints) >= 8  # Multiple AI features

# Path parameters (OpenAPI format)
param_endpoints = [ep for ep in result.endpoints if "{" in ep.path]
assert len(param_endpoints) >= 5  # :provider, :token, etc.

# Source tracking
for ep in result.endpoints:
    assert ep.source_file is not None
    assert ep.source_file.endswith(".js")
    assert ep.source_line is not None
    assert ep.source_line > 0

# Multiple methods per path (account management)
path_methods = {}
for ep in result.endpoints:
    if ep.path not in path_methods:
        path_methods[ep.path] = set()
    path_methods[ep.path].add(ep.method)

multi_method_paths = [p for p, methods in path_methods.items() if len(methods) > 1]
assert len(multi_method_paths) >= 10  # Many paths support GET + POST
```

### Key Validations
1. Core authentication endpoints (login, signup, logout)
2. OAuth provider endpoints (multiple providers)
3. Two-factor authentication flows
4. WebAuthn/passwordless authentication
5. Payment processing endpoints
6. API integration examples (Stripe, Twilio, etc.)
7. AI/ML feature endpoints
8. File upload endpoints
9. Account management endpoints
10. Path parameter extraction
11. Source file tracking
12. Multiple HTTP methods per path

## Notes

### Endpoint Count Considerations
The 106 endpoint estimate includes:
- **Web pages** (GET endpoints serving HTML via Pug templates)
- **API endpoints** (POST/GET endpoints returning JSON)
- **OAuth callbacks** (dynamic routes for each provider)
- **AI/ML features** (newer additions to the boilerplate)

The extractor may count fewer endpoints if it:
- Excludes template-rendering routes (web pages)
- Consolidates OAuth dynamic routes
- Skips middleware-only routes

This is acceptable - the focus is on extracting the API-style endpoints.

### Production Usage
Live demo: https://hackathon-starter-1.ydftech.com/
- Full working application
- All OAuth providers functional
- Payment integrations active
- AI/ML features enabled

### Architecture Insights
- Monolithic Express application (not microservices)
- Controller-based organization (`/controllers/`)
- Middleware-heavy architecture (Passport, Lusca, rate-limit, compression)
- MongoDB for persistence (users, sessions, vector embeddings)
- Environment-based configuration (development, production)
- Production checklist for deployment
- Comprehensive test coverage (unit, integration, E2E with Playwright)

### Diversity from RealWorld
This repository provides maximum contrast with node-express-realworld-example-app:
- **Domain:** Multi-service hub vs focused blogging
- **Endpoints:** 106 vs 19
- **Language:** JavaScript vs TypeScript
- **Auth:** 14+ strategies vs JWT only
- **Rendering:** Server-side (Pug) vs API-only
- **Payments:** Stripe + PayPal vs none
- **AI/ML:** LangChain + RAG vs none
- **Complexity:** High (production boilerplate) vs Medium (spec implementation)
